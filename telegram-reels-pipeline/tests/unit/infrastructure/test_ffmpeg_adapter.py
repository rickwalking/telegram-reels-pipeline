"""Tests for FFmpegAdapter — frame extraction, crop & encode, concat."""

from __future__ import annotations

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


class TestFFmpegAdapterProtocol:
    def test_satisfies_video_processing_port(self) -> None:
        from pipeline.domain.ports import VideoProcessingPort

        adapter = FFmpegAdapter()
        assert isinstance(adapter, VideoProcessingPort)
