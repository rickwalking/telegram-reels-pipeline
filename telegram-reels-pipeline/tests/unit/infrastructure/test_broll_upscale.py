"""Tests for ReelAssembler B-roll auto-upscale — probe, upscale, ensure resolution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.domain.models import BrollPlacement
from pipeline.infrastructure.adapters.reel_assembler import (
    AssemblyError,
    ReelAssembler,
)


def _mock_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


def _make_placement(
    variant: str = "broll",
    clip_path: str = "/tmp/clip.mp4",
    insertion_point_s: float = 10.0,
    duration_s: float = 6.0,
    narrative_anchor: str = "test anchor",
    match_confidence: float = 0.8,
) -> BrollPlacement:
    return BrollPlacement(
        variant=variant,
        clip_path=clip_path,
        insertion_point_s=insertion_point_s,
        duration_s=duration_s,
        narrative_anchor=narrative_anchor,
        match_confidence=match_confidence,
    )


class TestProbeResolution:
    """Tests for _probe_resolution static method."""

    async def test_returns_resolution_from_ffprobe(self) -> None:
        ffprobe_output = json.dumps({"streams": [{"width": 720, "height": 1280}]}).encode()
        mock_proc = _mock_process(returncode=0, stdout=ffprobe_output)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._probe_resolution(Path("/tmp/clip.mp4"))

        assert result == (720, 1280)

    async def test_returns_zero_tuple_on_ffprobe_failure(self) -> None:
        mock_proc = _mock_process(returncode=1, stderr=b"ffprobe error")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._probe_resolution(Path("/tmp/clip.mp4"))

        assert result == (0, 0)

    async def test_returns_zero_tuple_on_invalid_json(self) -> None:
        mock_proc = _mock_process(returncode=0, stdout=b"not json")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._probe_resolution(Path("/tmp/clip.mp4"))

        assert result == (0, 0)

    async def test_returns_zero_tuple_on_missing_stream_key(self) -> None:
        ffprobe_output = json.dumps({"streams": [{}]}).encode()
        mock_proc = _mock_process(returncode=0, stdout=ffprobe_output)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._probe_resolution(Path("/tmp/clip.mp4"))

        assert result == (0, 0)

    async def test_passes_correct_ffprobe_arguments(self) -> None:
        ffprobe_output = json.dumps({"streams": [{"width": 1080, "height": 1920}]}).encode()
        mock_proc = _mock_process(returncode=0, stdout=ffprobe_output)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            await ReelAssembler._probe_resolution(Path("/tmp/my_clip.mp4"))

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert call_args[0] == "ffprobe"
        assert "-select_streams" in call_args
        assert "v:0" in call_args
        assert "-show_entries" in call_args
        assert "stream=width,height" in call_args
        assert "-of" in call_args
        assert "json" in call_args
        assert "/tmp/my_clip.mp4" in call_args


class TestUpscaleClip:
    """Tests for _upscale_clip static method."""

    async def test_builds_correct_ffmpeg_command(self) -> None:
        mock_proc = _mock_process(returncode=0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._upscale_clip(Path("/tmp/src.mp4"), Path("/tmp/dest.mp4"))

        assert result == Path("/tmp/dest.mp4")
        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert call_args[0] == "ffmpeg"
        assert "-i" in call_args
        assert "/tmp/src.mp4" in call_args
        assert "-vf" in call_args
        assert "scale=1080:1920:flags=lanczos" in call_args
        assert "-c:a" in call_args
        assert "copy" in call_args
        assert "-y" in call_args
        assert "/tmp/dest.mp4" in call_args

    async def test_raises_assembly_error_on_failure(self) -> None:
        mock_proc = _mock_process(returncode=1, stderr=b"upscale error")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            with pytest.raises(AssemblyError, match="FFmpeg upscale failed"):
                await ReelAssembler._upscale_clip(Path("/tmp/src.mp4"), Path("/tmp/dest.mp4"))

    async def test_returns_dest_path_on_success(self) -> None:
        mock_proc = _mock_process(returncode=0)
        dest = Path("/tmp/output/upscaled.mp4")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=mock_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            result = await ReelAssembler._upscale_clip(Path("/tmp/src.mp4"), dest)

        assert result == dest


class TestEnsureClipResolution:
    """Tests for _ensure_clip_resolution method."""

    async def test_returns_original_path_when_already_target_resolution(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"video")
        assembler = ReelAssembler()

        with patch.object(ReelAssembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)):
            result = await assembler._ensure_clip_resolution(clip, tmp_path)

        assert result == clip

    async def test_upscales_when_not_target_resolution(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"video")
        temp_dir = tmp_path / "upscale_tmp"
        temp_dir.mkdir()
        assembler = ReelAssembler()

        with (
            patch.object(ReelAssembler, "_probe_resolution", new_callable=AsyncMock, return_value=(720, 1280)),
            patch.object(
                ReelAssembler,
                "_upscale_clip",
                new_callable=AsyncMock,
                return_value=temp_dir / "_upscaled_clip.mp4",
            ),
        ):
            result = await assembler._ensure_clip_resolution(clip, temp_dir)

        assert result == temp_dir / "_upscaled_clip.mp4"
        assert result != clip

    async def test_does_not_call_upscale_for_correct_resolution(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"video")
        assembler = ReelAssembler()

        with (
            patch.object(ReelAssembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)),
            patch.object(ReelAssembler, "_upscale_clip", new_callable=AsyncMock) as mock_upscale,
        ):
            await assembler._ensure_clip_resolution(clip, tmp_path)

        mock_upscale.assert_not_called()

    async def test_calls_upscale_with_correct_dest_name(self, tmp_path: Path) -> None:
        clip = tmp_path / "my-broll.mp4"
        clip.write_bytes(b"video")
        temp_dir = tmp_path / "up"
        temp_dir.mkdir()
        assembler = ReelAssembler()

        with (
            patch.object(ReelAssembler, "_probe_resolution", new_callable=AsyncMock, return_value=(640, 480)),
            patch.object(
                ReelAssembler,
                "_upscale_clip",
                new_callable=AsyncMock,
                return_value=temp_dir / "_upscaled_my-broll.mp4",
            ) as mock_upscale,
        ):
            await assembler._ensure_clip_resolution(clip, temp_dir)

        mock_upscale.assert_called_once_with(clip, temp_dir / "_upscaled_my-broll.mp4")


class TestAssembleWithBrollUpscale:
    """Tests for upscale integration in assemble_with_broll."""

    async def test_upscale_temp_dir_is_cleaned_up_on_success(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip))
        assembler = ReelAssembler()

        created_dirs: list[str] = []

        original_mkdtemp = __import__("tempfile").mkdtemp

        def tracking_mkdtemp(**kwargs: str) -> str:
            d = original_mkdtemp(**kwargs)
            created_dirs.append(d)
            return d

        with (
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(str(clip))),
            patch.object(assembler, "_assemble_with_cutaways", new_callable=AsyncMock, return_value=output),
            patch("pipeline.infrastructure.adapters.reel_assembler.tempfile") as mock_tempfile,
            patch("pipeline.infrastructure.adapters.reel_assembler.shutil") as mock_shutil,
        ):
            mock_tempfile.mkdtemp = tracking_mkdtemp
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

            # shutil.rmtree should have been called to clean up
            mock_shutil.rmtree.assert_called_once()

    async def test_upscale_temp_dir_cleaned_on_failure(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip))
        assembler = ReelAssembler()

        with (
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(str(clip))),
            patch.object(
                assembler, "_assemble_with_cutaways", new_callable=AsyncMock, side_effect=AssemblyError("boom")
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output),
            patch("pipeline.infrastructure.adapters.reel_assembler.tempfile") as mock_tempfile,
            patch("pipeline.infrastructure.adapters.reel_assembler.shutil") as mock_shutil,
        ):
            mock_tempfile.mkdtemp = MagicMock(return_value="/tmp/broll_upscale_test")
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

            # rmtree called even when cutaway fails
            mock_shutil.rmtree.assert_called_once_with(Path("/tmp/broll_upscale_test"), ignore_errors=True)

    async def test_upscaled_clip_path_used_in_placement(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"
        upscaled_path = tmp_path / "_upscaled_broll.mp4"

        placement = _make_placement(clip_path=str(clip))
        assembler = ReelAssembler()

        captured_placements: list[list[BrollPlacement]] = []

        async def capture_cutaways(
            segments: list[Path],
            out: Path,
            placements: list[BrollPlacement],
            transitions: tuple[object, ...] | None,
        ) -> Path:
            captured_placements.append(placements)
            return out

        with (
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=upscaled_path),
            patch.object(assembler, "_assemble_with_cutaways", side_effect=capture_cutaways),
            patch("pipeline.infrastructure.adapters.reel_assembler.tempfile") as mock_tempfile,
            patch("pipeline.infrastructure.adapters.reel_assembler.shutil"),
        ):
            mock_tempfile.mkdtemp = MagicMock(return_value="/tmp/broll_upscale_test")
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        assert len(captured_placements) == 1
        assert captured_placements[0][0].clip_path == str(upscaled_path)

    async def test_unchanged_clip_path_when_already_correct_resolution(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip))
        assembler = ReelAssembler()

        captured_placements: list[list[BrollPlacement]] = []

        async def capture_cutaways(
            segments: list[Path],
            out: Path,
            placements: list[BrollPlacement],
            transitions: tuple[object, ...] | None,
        ) -> Path:
            captured_placements.append(placements)
            return out

        with (
            patch.object(
                assembler,
                "_ensure_clip_resolution",
                new_callable=AsyncMock,
                return_value=Path(str(clip)),
            ),
            patch.object(assembler, "_assemble_with_cutaways", side_effect=capture_cutaways),
            patch("pipeline.infrastructure.adapters.reel_assembler.tempfile") as mock_tempfile,
            patch("pipeline.infrastructure.adapters.reel_assembler.shutil"),
        ):
            mock_tempfile.mkdtemp = MagicMock(return_value="/tmp/broll_upscale_test")
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        assert len(captured_placements) == 1
        # clip_path should be unchanged since _ensure returned the same path
        assert captured_placements[0][0].clip_path == str(clip)
