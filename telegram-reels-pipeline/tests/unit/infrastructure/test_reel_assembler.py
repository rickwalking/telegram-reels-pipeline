"""Tests for ReelAssembler — video segment concatenation and validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.infrastructure.adapters.reel_assembler import AssemblyError, ReelAssembler, TransitionSpec


def _mock_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


class TestReelAssemblerAssemble:
    async def test_single_segment_copies_file(self, tmp_path: Path) -> None:
        seg = tmp_path / "segment.mp4"
        seg.write_bytes(b"video-content")
        output = tmp_path / "reel.mp4"

        assembler = ReelAssembler()
        result = await assembler.assemble([seg], output)
        assert result == output
        assert output.read_bytes() == b"video-content"

    async def test_multiple_segments_calls_ffmpeg(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "reel.mp4"

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble([seg1, seg2], output)

        mock_aio.create_subprocess_exec.assert_called_once()
        # Verify concat args
        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "ffmpeg" in call_args
        assert "-f" in call_args
        assert "concat" in call_args

    async def test_raises_on_empty_segments(self) -> None:
        assembler = ReelAssembler()
        with pytest.raises(AssemblyError, match="must not be empty"):
            await assembler.assemble([], Path("out.mp4"))

    async def test_raises_on_missing_segment(self, tmp_path: Path) -> None:
        assembler = ReelAssembler()
        with pytest.raises(AssemblyError, match="not found"):
            await assembler.assemble([tmp_path / "missing.mp4"], tmp_path / "out.mp4")

    async def test_creates_output_directory(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"data")
        output = tmp_path / "deep" / "nested" / "reel.mp4"

        assembler = ReelAssembler()
        await assembler.assemble([seg], output)
        assert output.exists()

    async def test_ffmpeg_failure_raises(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                return_value=_mock_process(returncode=1, stderr=b"concat error")
            )
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            with pytest.raises(AssemblyError, match="FFmpeg concat failed"):
                await assembler.assemble([seg1, seg2], tmp_path / "out.mp4")

    async def test_cleans_up_list_file(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "reel.mp4"

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble([seg1, seg2], output)

        # No temporary list file should remain
        txt_files = list(tmp_path.glob("_assembly_*.txt"))
        assert len(txt_files) == 0


class TestTransitionSpec:
    def test_frozen(self) -> None:
        spec = TransitionSpec(offset_seconds=19.5)
        with pytest.raises(AttributeError):
            spec.offset_seconds = 10.0  # type: ignore[misc]

    def test_defaults(self) -> None:
        spec = TransitionSpec(offset_seconds=5.0)
        assert spec.effect == "fade"
        assert spec.duration == 0.5

    def test_custom_values(self) -> None:
        spec = TransitionSpec(offset_seconds=10.0, effect="slideright", duration=1.0)
        assert spec.effect == "slideright"
        assert spec.duration == 1.0


class TestBuildXfadeFilter:
    def test_two_segments_one_transition(self) -> None:
        transitions = (TransitionSpec(offset_seconds=19.5),)
        result = ReelAssembler._build_xfade_filter(2, transitions)
        assert "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=19.5[v]" in result
        assert "[0:a][1:a]acrossfade=d=0.5[a]" in result

    def test_three_segments_two_transitions(self) -> None:
        transitions = (
            TransitionSpec(offset_seconds=19.5, effect="fade"),
            TransitionSpec(offset_seconds=38.5, effect="slideright"),
        )
        result = ReelAssembler._build_xfade_filter(3, transitions)
        assert "[0:v][1:v]xfade" in result
        assert "[vtmp1][2:v]xfade" in result
        assert "[0:a][1:a]acrossfade" in result
        assert "[atmp1][2:a]acrossfade" in result
        assert "[v]" in result
        assert "[a]" in result

    def test_mismatched_count_raises(self) -> None:
        with pytest.raises(AssemblyError, match="Expected 2 transitions"):
            ReelAssembler._build_xfade_filter(3, (TransitionSpec(offset_seconds=10.0),))


class TestReelAssemblerXfade:
    async def test_xfade_calls_ffmpeg_with_filter_complex(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "reel.mp4"
        transitions = (TransitionSpec(offset_seconds=19.5),)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble([seg1, seg2], output, transitions=transitions)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "ffmpeg" in call_args
        assert "-filter_complex" in call_args
        assert "-map" in call_args
        # Verify both video and audio are mapped
        map_indices = [i for i, a in enumerate(call_args) if a == "-map"]
        mapped_streams = {call_args[i + 1] for i in map_indices}
        assert "[v]" in mapped_streams
        assert "[a]" in mapped_streams

    async def test_xfade_failure_falls_back_to_concat(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "reel.mp4"
        transitions = (TransitionSpec(offset_seconds=19.5),)

        xfade_proc = _mock_process(returncode=1, stderr=b"xfade error")
        concat_proc = _mock_process(returncode=0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=[xfade_proc, concat_proc])
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.assemble([seg1, seg2], output, transitions=transitions)

        assert result == output
        assert mock_aio.create_subprocess_exec.call_count == 2
        # First call: xfade (filter_complex), second call: concat
        first_call_args = mock_aio.create_subprocess_exec.call_args_list[0][0]
        second_call_args = mock_aio.create_subprocess_exec.call_args_list[1][0]
        assert "-filter_complex" in first_call_args
        assert "concat" in second_call_args

    async def test_xfade_and_concat_both_fail_raises(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        transitions = (TransitionSpec(offset_seconds=19.5),)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(returncode=1, stderr=b"error"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            with pytest.raises(AssemblyError, match="FFmpeg concat failed"):
                await assembler.assemble([seg1, seg2], tmp_path / "out.mp4", transitions=transitions)

    async def test_no_transitions_uses_concat(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        output = tmp_path / "reel.mp4"

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble([seg1, seg2], output)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "concat" in call_args
        assert "-filter_complex" not in call_args


class TestReelAssemblerValidateDuration:
    async def test_valid_duration(self) -> None:
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"75.5\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.validate_duration(Path("reel.mp4"))

        assert result is True

    async def test_too_short(self) -> None:
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"10.0\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.validate_duration(Path("reel.mp4"))

        assert result is False

    async def test_too_long(self) -> None:
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"200.0\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.validate_duration(Path("reel.mp4"))

        assert result is False

    async def test_ffprobe_failure_returns_false(self) -> None:
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(returncode=1, stderr=b"error"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.validate_duration(Path("reel.mp4"))

        assert result is False

    async def test_custom_duration_bounds(self) -> None:
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process(stdout=b"15.0\n"))
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler.validate_duration(
                Path("reel.mp4"),
                min_duration=10.0,
                max_duration=20.0,
            )

        assert result is True
