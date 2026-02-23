"""Tests for FFmpegAdapter — frame extraction, crop & encode, concat, encoding plan."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.domain.models import CropRegion, SegmentLayout
from pipeline.infrastructure.adapters.ffmpeg_adapter import FFmpegAdapter, FFmpegError


def _mock_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


class TestFFmpegAdapterExtractFrames:
    async def test_extracts_frames_at_timestamps(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            frames = await adapter.extract_frames(video, [1.0, 5.5, 10.0])

        assert len(frames) == 3
        assert all(f.name.startswith("frame_") for f in frames)
        assert mock_aio.create_subprocess_exec.call_count == 3

    async def test_raises_on_missing_video(self, tmp_path: Path) -> None:
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="not found"):
            await adapter.extract_frames(tmp_path / "missing.mp4", [1.0])

    async def test_raises_on_ffmpeg_failure(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(returncode=1, stderr=b"error"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="Failed to extract frame"):
                await adapter.extract_frames(video, [1.0])


class TestFFmpegAdapterCropAndEncode:
    def _segment(
        self,
        start: float = 0.0,
        end: float = 60.0,
        layout: str = "side_by_side",
    ) -> SegmentLayout:
        return SegmentLayout(
            start_seconds=start,
            end_seconds=end,
            layout_name=layout,
            crop_region=CropRegion(x=0, y=0, width=540, height=1080, layout_name=layout),
        )

    async def test_single_segment_no_concat(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "output.mp4"

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.crop_and_encode(video, [self._segment()], output)

        assert result == output
        # Only one ffmpeg call (no concat needed)
        assert mock_aio.create_subprocess_exec.call_count == 1

    async def test_multiple_segments_encode_and_concat(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "output.mp4"

        seg1 = self._segment(start=0.0, end=30.0)
        seg2 = self._segment(start=30.0, end=60.0, layout="speaker_focus")

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.crop_and_encode(video, [seg1, seg2], output)

        assert result == output
        # 2 encode calls + 1 concat call = 3
        assert mock_aio.create_subprocess_exec.call_count == 3

    async def test_raises_on_empty_segments(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="must not be empty"):
            await adapter.crop_and_encode(video, [], tmp_path / "out.mp4")

    async def test_raises_on_missing_crop_region(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        seg = SegmentLayout(start_seconds=0, end_seconds=60, layout_name="unknown")
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="crop_region required"):
            await adapter.crop_and_encode(video, [seg], tmp_path / "out.mp4")

    async def test_uses_configured_threads(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "output.mp4"

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter(threads=4)
            await adapter.crop_and_encode(video, [self._segment()], output)

        # Check threads arg was passed
        call_args = mock_aio.create_subprocess_exec.call_args
        assert "4" in call_args[0]

    async def test_crop_filter_format(self, tmp_path: Path) -> None:
        video = tmp_path / "input.mp4"
        video.write_bytes(b"fake")
        output = tmp_path / "output.mp4"
        seg = SegmentLayout(
            start_seconds=10.0,
            end_seconds=70.0,
            layout_name="test",
            crop_region=CropRegion(x=100, y=50, width=540, height=960),
        )

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.crop_and_encode(video, [seg], output)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        # Should contain crop=540:960:100:50 and scale=1080:1920
        vf_idx = list(call_args).index("-vf")
        vf_value = call_args[vf_idx + 1]
        assert "crop=540:960:100:50" in vf_value
        assert "scale=1080:1920" in vf_value


class TestFFmpegAdapterConcatVideos:
    async def test_single_video_copies(self, tmp_path: Path) -> None:
        src = tmp_path / "seg.mp4"
        src.write_bytes(b"video-data")
        output = tmp_path / "out.mp4"

        adapter = FFmpegAdapter()
        result = await adapter.concat_videos([src], output)
        assert result == output
        assert output.read_bytes() == b"video-data"

    async def test_multiple_videos_concat(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "out.mp4"

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.concat_videos([seg1, seg2], output)

        mock_aio.create_subprocess_exec.assert_called_once()

    async def test_raises_on_empty_list(self) -> None:
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="must not be empty"):
            await adapter.concat_videos([], Path("out.mp4"))


class TestFFmpegAdapterProbeDuration:
    async def test_returns_duration(self) -> None:
        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"65.432\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            duration = await adapter.probe_duration(Path("test.mp4"))

        assert duration == pytest.approx(65.432)

    async def test_raises_on_failure(self) -> None:
        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(returncode=1, stderr=b"err"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="ffprobe failed"):
                await adapter.probe_duration(Path("test.mp4"))

    async def test_raises_on_bad_output(self) -> None:
        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"not-a-number\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="Could not parse"):
                await adapter.probe_duration(Path("test.mp4"))


def _ffmpeg_side_effect(*args: object, **kwargs: object) -> MagicMock:
    """Simulate ffmpeg creating the output file (last positional arg)."""
    output_arg = str(args[-1]) if args else ""
    if output_arg.endswith(".mp4"):
        Path(output_arg).write_bytes(b"fake-video")
    return _mock_process()


class TestFFmpegAdapterExecuteEncodingPlan:
    """Tests for execute_encoding_plan — the bridge between agent plans and ffmpeg execution."""

    def _make_plan(
        self,
        tmp_path: Path,
        commands: list[dict[str, object]] | None = None,
        extra_fields: dict[str, object] | None = None,
    ) -> Path:
        """Create an encoding-plan.json for testing."""
        if commands is None:
            commands = [
                {
                    "input": str(tmp_path / "source.mp4"),
                    "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos,setsar=1",
                    "output": str(tmp_path / "segment-001.mp4"),
                    "start_seconds": 100.0,
                    "end_seconds": 130.0,
                },
            ]
        plan: dict[str, object] = {
            "commands": commands,
            "segment_paths": [c["output"] for c in commands],
            "total_duration_seconds": sum(
                float(c.get("end_seconds", 0)) - float(c.get("start_seconds", 0)) for c in commands
            ),
        }
        if extra_fields:
            plan.update(extra_fields)
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(json.dumps(plan))
        return plan_path

    # ------------------------------------------------------------------
    # Basic happy paths
    # ------------------------------------------------------------------

    async def test_executes_single_command(self, tmp_path: Path) -> None:
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1
        assert result[0] == tmp_path / "segment-001.mp4"
        mock_aio.create_subprocess_exec.assert_called_once()

    async def test_executes_multiple_commands(self, tmp_path: Path) -> None:
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=608:1080:280:0,scale=1080:1920",
                "output": str(tmp_path / "segment-002.mp4"),
                "start_seconds": 130.0,
                "end_seconds": 160.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 2
        assert result[0].name == "segment-001.mp4"
        assert result[1].name == "segment-002.mp4"
        assert mock_aio.create_subprocess_exec.call_count == 2

    async def test_many_segments_ten(self, tmp_path: Path) -> None:
        """Verify the adapter scales to 10 segments without issue."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": f"crop=960:1080:{i * 10}:0,scale=1080:1920",
                "output": str(tmp_path / f"segment-{i + 1:03d}.mp4"),
                "start_seconds": float(i * 10),
                "end_seconds": float((i + 1) * 10),
            }
            for i in range(10)
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 10
        assert mock_aio.create_subprocess_exec.call_count == 10
        assert result[0].name == "segment-001.mp4"
        assert result[9].name == "segment-010.mp4"

    # ------------------------------------------------------------------
    # Multi-moment narrative scenarios
    # ------------------------------------------------------------------

    async def test_multi_moment_three_moments_five_segments(self, tmp_path: Path) -> None:
        """Realistic 3-moment narrative: intro(1 seg) + core(2 segs) + conclusion(2 segs)."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos,setsar=1",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 120.0,
                "end_seconds": 150.0,
                "moment_index": 0,
                "narrative_role": "intro",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos,setsar=1",
                "output": str(tmp_path / "segment-002.mp4"),
                "start_seconds": 300.0,
                "end_seconds": 330.0,
                "moment_index": 1,
                "narrative_role": "core",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=608:1080:280:0,scale=1080:1920:flags=lanczos,setsar=1",
                "output": str(tmp_path / "segment-003.mp4"),
                "start_seconds": 330.0,
                "end_seconds": 360.0,
                "moment_index": 1,
                "narrative_role": "core",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos,setsar=1",
                "output": str(tmp_path / "segment-004.mp4"),
                "start_seconds": 600.0,
                "end_seconds": 620.0,
                "moment_index": 2,
                "narrative_role": "conclusion",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=608:1080:280:0,scale=1080:1920:flags=lanczos,setsar=1",
                "output": str(tmp_path / "segment-005.mp4"),
                "start_seconds": 620.0,
                "end_seconds": 650.0,
                "moment_index": 2,
                "narrative_role": "conclusion",
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 5
        assert mock_aio.create_subprocess_exec.call_count == 5
        # Verify global sequential numbering across all moments
        assert [p.name for p in result] == [
            "segment-001.mp4",
            "segment-002.mp4",
            "segment-003.mp4",
            "segment-004.mp4",
            "segment-005.mp4",
        ]

    async def test_multi_moment_max_five_moments(self, tmp_path: Path) -> None:
        """Max narrative: 5 moments with all role types."""
        roles = ["intro", "buildup", "core", "reaction", "conclusion"]
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / f"segment-{i + 1:03d}.mp4"),
                "start_seconds": float(i * 60),
                "end_seconds": float(i * 60 + 30),
                "moment_index": i,
                "narrative_role": roles[i],
            }
            for i in range(5)
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 5
        assert mock_aio.create_subprocess_exec.call_count == 5

    async def test_single_moment_with_narrative_fields(self, tmp_path: Path) -> None:
        """Explicit --moments 1: single moment with narrative metadata still works."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 190.0,
                "moment_index": 0,
                "narrative_role": "core",
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1

    # ------------------------------------------------------------------
    # Filter type variations
    # ------------------------------------------------------------------

    async def test_uses_filter_complex_when_specified(self, tmp_path: Path) -> None:
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "",
                "filter_type": "filter_complex",
                "filter_complex": "[0:v]split=2[left][right];[left]crop=960:1080:0:0[l];[right]crop=960:1080:960:0[r]",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        assert "-filter_complex" in call_args
        assert "-vf" not in call_args
        # filter_complex must use labeled output pad mapping
        map_indices = [i for i, a in enumerate(call_args) if a == "-map"]
        assert len(map_indices) == 2, f"Expected 2 -map args, got {len(map_indices)}"
        assert call_args[map_indices[0] + 1] == "[v]"
        assert call_args[map_indices[1] + 1] == "0:a?"

    async def test_filter_type_crop_explicit(self, tmp_path: Path) -> None:
        """Explicitly set filter_type='crop' — should use -vf."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "filter_type": "crop",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "-vf" in call_args
        assert "-filter_complex" not in call_args

    async def test_filter_complex_null_falls_back_to_crop(self, tmp_path: Path) -> None:
        """filter_type='filter_complex' but filter_complex is null — falls back to crop_filter."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "filter_type": "filter_complex",
                "filter_complex": None,
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        # Should fall back to -vf since filter_complex is None
        assert "-vf" in call_args
        assert "-filter_complex" not in call_args

    async def test_mixed_crop_and_filter_complex_commands(self, tmp_path: Path) -> None:
        """Some segments use crop, others use filter_complex (auto FSM style transitions)."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "filter_type": "crop",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 120.0,
                "framing_style_state": "solo",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "",
                "filter_type": "filter_complex",
                "filter_complex": (
                    "[0:v]split=2[l][r];[l]crop=960:1080:0:0,scale=540:960[lo];"
                    "[r]crop=960:1080:960:0,scale=540:960[ro];[lo][ro]vstack[v]"
                ),
                "output": str(tmp_path / "segment-002.mp4"),
                "start_seconds": 120.0,
                "end_seconds": 140.0,
                "framing_style_state": "duo_split",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=608:1080:280:0,scale=1080:1920",
                "filter_type": "crop",
                "output": str(tmp_path / "segment-003.mp4"),
                "start_seconds": 140.0,
                "end_seconds": 160.0,
                "framing_style_state": "solo",
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 3
        calls = mock_aio.create_subprocess_exec.call_args_list
        # First call: -vf (crop), no -map
        assert "-vf" in calls[0][0]
        assert "-filter_complex" not in calls[0][0]
        assert "-map" not in calls[0][0]
        # Second call: -filter_complex (split-screen) with -map [v] -map 0:a?
        call1_args = list(calls[1][0])
        assert "-filter_complex" in call1_args
        assert "-vf" not in call1_args
        map_indices = [i for i, a in enumerate(call1_args) if a == "-map"]
        assert len(map_indices) == 2
        assert call1_args[map_indices[0] + 1] == "[v]"
        assert call1_args[map_indices[1] + 1] == "0:a?"
        # Third call: -vf (crop), no -map
        assert "-vf" in calls[2][0]
        assert "-filter_complex" not in calls[2][0]
        assert "-map" not in calls[2][0]

    # ------------------------------------------------------------------
    # Encoding parameters & argument ordering
    # ------------------------------------------------------------------

    async def test_uses_correct_encoding_params(self, tmp_path: Path) -> None:
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        assert "libx264" in call_args
        assert "main" in call_args
        assert "23" in call_args
        assert "medium" in call_args
        assert "yuv420p" in call_args
        assert "aac" in call_args
        assert "128k" in call_args
        assert "+faststart" in call_args

    async def test_ss_and_to_before_input_for_fast_seeking(self, tmp_path: Path) -> None:
        """FFmpeg seeks faster when -ss/-to appear before -i (input seeking)."""
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        ss_idx = call_args.index("-ss")
        to_idx = call_args.index("-to")
        i_idx = call_args.index("-i")
        assert ss_idx < i_idx, f"-ss at {ss_idx} should come before -i at {i_idx}"
        assert to_idx < i_idx, f"-to at {to_idx} should come before -i at {i_idx}"

    async def test_timestamps_passed_as_strings(self, tmp_path: Path) -> None:
        """Float timestamps must be stringified for subprocess args."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 1247.5,
                "end_seconds": 1325.75,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        ss_idx = call_args.index("-ss")
        to_idx = call_args.index("-to")
        assert call_args[ss_idx + 1] == "1247.5"
        assert call_args[to_idx + 1] == "1325.75"

    async def test_uses_configured_threads(self, tmp_path: Path) -> None:
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter(threads=4)
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        threads_idx = call_args.index("-threads")
        assert call_args[threads_idx + 1] == "4"

    async def test_default_threads_is_two(self, tmp_path: Path) -> None:
        """Pi default: 2 threads to limit memory."""
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()  # default threads
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        threads_idx = call_args.index("-threads")
        assert call_args[threads_idx + 1] == "2"

    # ------------------------------------------------------------------
    # Extra fields in plan (should be ignored by adapter)
    # ------------------------------------------------------------------

    async def test_ignores_extra_fields_in_commands(self, tmp_path: Path) -> None:
        """boundary_validation, framing_style_state, quality, validation — all ignored."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
                "framing_style_state": "duo_split",
                "boundary_validation": {
                    "start_face_count": 2,
                    "end_face_count": 2,
                    "expected_face_count": 2,
                    "start_trimmed": False,
                    "end_trimmed": False,
                },
                "validation": {
                    "face_in_crop": True,
                    "face_source": "Speaker_Left",
                    "active_speaker": "A",
                },
                "quality": {
                    "upscale_factor": 1.125,
                    "quality": "good",
                    "recommendation": "proceed",
                },
                "moment_index": 0,
                "narrative_role": "core",
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1

    async def test_ignores_style_transitions_in_plan(self, tmp_path: Path) -> None:
        """Top-level style_transitions array is present but should not affect execution."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        extra = {
            "style_transitions": [
                {
                    "timestamp": 120.0,
                    "from_state": "solo",
                    "to_state": "duo_split",
                    "trigger": "face_count_increase",
                    "effect": None,
                    "transition_kind": "style_change",
                },
            ],
        }
        plan_path = self._make_plan(tmp_path, commands, extra_fields=extra)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1

    async def test_ignores_narrative_boundary_transitions(self, tmp_path: Path) -> None:
        """Multi-moment plan with narrative_boundary transitions in style_transitions."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
                "moment_index": 0,
                "narrative_role": "intro",
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-002.mp4"),
                "start_seconds": 300.0,
                "end_seconds": 330.0,
                "moment_index": 1,
                "narrative_role": "core",
            },
        ]
        extra = {
            "style_transitions": [
                {
                    "timestamp": 300.0,
                    "from_state": "solo",
                    "to_state": "solo",
                    "trigger": "narrative_boundary",
                    "effect": "dissolve",
                    "transition_kind": "narrative_boundary",
                },
            ],
        }
        plan_path = self._make_plan(tmp_path, commands, extra_fields=extra)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 2

    # ------------------------------------------------------------------
    # Path handling
    # ------------------------------------------------------------------

    async def test_creates_output_parent_directories(self, tmp_path: Path) -> None:
        """Output in a nested path that doesn't exist yet — adapter should create it."""
        nested_output = str(tmp_path / "deep" / "nested" / "dir" / "segment-001.mp4")
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": nested_output,
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1
        assert result[0] == Path(nested_output)
        assert result[0].parent.exists()

    async def test_handles_paths_with_spaces(self, tmp_path: Path) -> None:
        """Paths containing spaces should be passed correctly to ffmpeg."""
        space_dir = tmp_path / "my workspace" / "run 2026"
        space_dir.mkdir(parents=True)
        source = space_dir / "source video.mp4"
        source.write_bytes(b"fake")

        commands = [
            {
                "input": str(source),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(space_dir / "segment 001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1
        # Verify input path with spaces was passed correctly
        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        assert str(source) in call_args
        # Output goes to a tmp file first (atomic write), then renamed to final path
        assert result[0] == Path(space_dir / "segment 001.mp4").resolve()

    # ------------------------------------------------------------------
    # Error scenarios
    # ------------------------------------------------------------------

    async def test_raises_on_missing_plan(self, tmp_path: Path) -> None:
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="not found"):
            await adapter.execute_encoding_plan(tmp_path / "missing.json")

    async def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text("not valid json{{{")
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="Invalid encoding plan"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_empty_commands(self, tmp_path: Path) -> None:
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(json.dumps({"commands": []}))
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="no commands"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_missing_commands_key(self, tmp_path: Path) -> None:
        """Plan JSON has no 'commands' key at all — default is empty list, should raise."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(json.dumps({"segment_paths": [], "total_duration_seconds": 0}))
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="no commands"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_ffmpeg_failure(self, tmp_path: Path) -> None:
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                return_value=_mock_process(returncode=1, stderr=b"encoding error")
            )
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="FFmpeg failed"):
                await adapter.execute_encoding_plan(plan_path)

    async def test_second_command_fails_first_segment_still_exists(self, tmp_path: Path) -> None:
        """When command 2 fails, command 1's output should remain on disk."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=608:1080:280:0,scale=1080:1920",
                "output": str(tmp_path / "segment-002.mp4"),
                "start_seconds": 130.0,
                "end_seconds": 160.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        call_count = [0]

        def _fail_on_second(*args: object, **kwargs: object) -> MagicMock:
            call_count[0] += 1
            if call_count[0] == 1:
                # First command succeeds
                output_arg = str(args[-1]) if args else ""
                if output_arg.endswith(".mp4"):
                    Path(output_arg).write_bytes(b"fake-video")
                return _mock_process()
            # Second command fails
            return _mock_process(returncode=1, stderr=b"disk full")

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_fail_on_second)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="FFmpeg failed"):
                await adapter.execute_encoding_plan(plan_path)

        # First segment should still exist on disk
        assert (tmp_path / "segment-001.mp4").exists()
        # Second segment was never created
        assert not (tmp_path / "segment-002.mp4").exists()

    async def test_raises_on_output_not_created(self, tmp_path: Path) -> None:
        """FFmpeg exits 0 but doesn't create the output file — should raise."""
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            # FFmpeg "succeeds" but creates no file
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError, match="produced no output"):
                await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_command_missing_output_field(self, tmp_path: Path) -> None:
        """Command without 'output' field — should raise FFmpegError."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "commands": [
                        {
                            "input": str(tmp_path / "source.mp4"),
                            "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                            "start_seconds": 100.0,
                            "end_seconds": 130.0,
                        },
                    ],
                }
            )
        )

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="missing required field"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_command_missing_input_field(self, tmp_path: Path) -> None:
        """Command without 'input' field — should raise FFmpegError."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "commands": [
                        {
                            "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                            "output": str(tmp_path / "segment-001.mp4"),
                            "start_seconds": 100.0,
                            "end_seconds": 130.0,
                        },
                    ],
                }
            )
        )

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="missing required field"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_binary_plan_file(self, tmp_path: Path) -> None:
        """Binary/corrupt file — should raise with 'Invalid encoding plan'."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_bytes(b"\xff\xfe\x00\x01\x80\x90")
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="Invalid encoding plan"):
            await adapter.execute_encoding_plan(plan_path)

    # ------------------------------------------------------------------
    # filter_type edge cases
    # ------------------------------------------------------------------

    async def test_filter_type_absent_defaults_to_crop(self, tmp_path: Path) -> None:
        """When filter_type is not in the command at all, default to 'crop' (uses -vf)."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
                # No filter_type key
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "-vf" in call_args
        assert "-filter_complex" not in call_args

    async def test_filter_complex_empty_string_falls_back_to_crop(self, tmp_path: Path) -> None:
        """filter_type='filter_complex' but filter_complex is '' — falls back to crop_filter."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "filter_type": "filter_complex",
                "filter_complex": "",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "-vf" in call_args
        assert "-filter_complex" not in call_args

    # ------------------------------------------------------------------
    # Crop filter content
    # ------------------------------------------------------------------

    async def test_crop_filter_value_passed_verbatim(self, tmp_path: Path) -> None:
        """The exact crop_filter string is passed to -vf without modification."""
        crop = "crop=608:1080:280:0,scale=1080:1920:flags=lanczos,setsar=1"
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": crop,
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        vf_idx = call_args.index("-vf")
        assert call_args[vf_idx + 1] == crop

    async def test_filter_complex_value_passed_verbatim(self, tmp_path: Path) -> None:
        """The exact filter_complex graph is passed to -filter_complex without modification."""
        fc = (
            "[0:v]split=2[l][r];[l]crop=960:1080:0:0,scale=540:960[lo];"
            "[r]crop=960:1080:960:0,scale=540:960[ro];[lo][ro]vstack[v]"
        )
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "",
                "filter_type": "filter_complex",
                "filter_complex": fc,
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        fc_idx = call_args.index("-filter_complex")
        assert call_args[fc_idx + 1] == fc
        # filter_complex must include -map [v] -map 0:a?
        map_indices = [i for i, a in enumerate(call_args) if a == "-map"]
        assert len(map_indices) == 2
        assert call_args[map_indices[0] + 1] == "[v]"
        assert call_args[map_indices[1] + 1] == "0:a?"

    async def test_filter_complex_without_v_label_gets_appended(self, tmp_path: Path) -> None:
        """When filter_complex output is unlabeled, adapter appends [v] for -map."""
        fc_no_label = (
            "split=2[top][bot];[top]crop=960:1080:17:0,scale=1080:960:flags=lanczos[t];"
            "[bot]crop=960:1080:930:0,scale=1080:960:flags=lanczos[b];"
            "[t][b]vstack,drawbox=x=0:y=957:w=1080:h=6:color=white@0.8:t=fill,setsar=1"
        )
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "",
                "filter_type": "filter_complex",
                "filter_complex": fc_no_label,
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            await adapter.execute_encoding_plan(plan_path)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        fc_idx = call_args.index("-filter_complex")
        # [v] should be appended to the filter graph
        assert call_args[fc_idx + 1].endswith("[v]")
        # -map [v] and -map 0:a? must still be present
        map_indices = [i for i, a in enumerate(call_args) if a == "-map"]
        assert len(map_indices) == 2
        assert call_args[map_indices[0] + 1] == "[v]"
        assert call_args[map_indices[1] + 1] == "0:a?"

    # ------------------------------------------------------------------
    # Return value correctness
    # ------------------------------------------------------------------

    async def test_returns_paths_in_command_order(self, tmp_path: Path) -> None:
        """Returned paths must match the order of commands in the plan."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-003.mp4"),
                "start_seconds": 200.0,
                "end_seconds": 230.0,
            },
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        # Must respect command order, not alphabetical
        assert result[0].name == "segment-003.mp4"
        assert result[1].name == "segment-001.mp4"

    async def test_returned_paths_are_absolute(self, tmp_path: Path) -> None:
        """Paths returned should be Path objects matching the plan output field."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path)

        assert len(result) == 1
        assert isinstance(result[0], Path)
        assert result[0].is_absolute()

    # ------------------------------------------------------------------
    # Path confinement (workspace escape prevention)
    # ------------------------------------------------------------------

    async def test_rejects_output_path_outside_workspace(self, tmp_path: Path) -> None:
        """Output path escaping the workspace should raise FFmpegError."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": "/tmp/evil/segment-001.mp4",
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="escapes workspace"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_rejects_input_path_outside_workspace(self, tmp_path: Path) -> None:
        """Input path escaping the workspace should raise FFmpegError."""
        commands = [
            {
                "input": "/etc/passwd",
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="escapes workspace"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_explicit_workspace_confines_paths(self, tmp_path: Path) -> None:
        """When workspace is explicit, paths must be within it."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        plan_dir = tmp_path / "plans"
        plan_dir.mkdir()

        commands = [
            {
                "input": str(workspace / "source.mp4"),
                "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                "output": str(workspace / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = plan_dir / "encoding-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "commands": commands,
                    "segment_paths": [c["output"] for c in commands],
                    "total_duration_seconds": 30.0,
                }
            )
        )

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=_ffmpeg_side_effect)
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            result = await adapter.execute_encoding_plan(plan_path, workspace=workspace)

        assert len(result) == 1

    # ------------------------------------------------------------------
    # Atomic write behavior
    # ------------------------------------------------------------------

    async def test_atomic_write_cleans_up_tmp_on_ffmpeg_failure(self, tmp_path: Path) -> None:
        """When ffmpeg fails, the tmp file should be cleaned up."""
        plan_path = self._make_plan(tmp_path)

        with patch("pipeline.infrastructure.adapters.ffmpeg_adapter.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(returncode=1, stderr=b"error"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            adapter = FFmpegAdapter()
            with pytest.raises(FFmpegError):
                await adapter.execute_encoding_plan(plan_path)

        # No .tmp.mp4 files should remain
        tmp_files = list(tmp_path.glob("*.tmp.mp4"))
        assert tmp_files == [], f"Leftover tmp files: {tmp_files}"

    async def test_raises_on_plan_root_not_object(self, tmp_path: Path) -> None:
        """Plan JSON root is a list instead of dict — should raise FFmpegError."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(json.dumps([{"commands": []}]))
        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="must be an object"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_missing_start_seconds(self, tmp_path: Path) -> None:
        """Command without 'start_seconds' — should raise FFmpegError."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "commands": [
                        {
                            "input": str(tmp_path / "source.mp4"),
                            "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                            "output": str(tmp_path / "segment-001.mp4"),
                            "end_seconds": 130.0,
                        },
                    ],
                }
            )
        )

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="missing required field"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_raises_on_missing_end_seconds(self, tmp_path: Path) -> None:
        """Command without 'end_seconds' — should raise FFmpegError."""
        plan_path = tmp_path / "encoding-plan.json"
        plan_path.write_text(
            json.dumps(
                {
                    "commands": [
                        {
                            "input": str(tmp_path / "source.mp4"),
                            "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
                            "output": str(tmp_path / "segment-001.mp4"),
                            "start_seconds": 100.0,
                        },
                    ],
                }
            )
        )

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="missing required field"):
            await adapter.execute_encoding_plan(plan_path)

    async def test_missing_crop_filter_raises(self, tmp_path: Path) -> None:
        """Command with no crop_filter and no filter_complex — should raise FFmpegError."""
        commands = [
            {
                "input": str(tmp_path / "source.mp4"),
                "output": str(tmp_path / "segment-001.mp4"),
                "start_seconds": 100.0,
                "end_seconds": 130.0,
            },
        ]
        plan_path = self._make_plan(tmp_path, commands)

        adapter = FFmpegAdapter()
        with pytest.raises(FFmpegError, match="missing crop_filter"):
            await adapter.execute_encoding_plan(plan_path)


class TestFFmpegAdapterProtocol:
    def test_satisfies_video_processing_port(self) -> None:
        from pipeline.domain.ports import VideoProcessingPort

        adapter = FFmpegAdapter()
        assert isinstance(adapter, VideoProcessingPort)
