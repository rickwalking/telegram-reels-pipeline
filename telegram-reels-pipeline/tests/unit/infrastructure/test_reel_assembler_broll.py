"""Tests for ReelAssembler B-roll — cutaway filter and assemble_with_broll."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.domain.models import BrollPlacement, CutawayManifest
from pipeline.infrastructure.adapters.reel_assembler import (
    ReelAssembler,
    TransitionSpec,
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


class TestBuildCutawayFilter:
    """Tests for _build_cutaway_filter static method."""

    def test_produces_valid_filter_string(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_overlay_with_time_bounds(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
        )
        assert "overlay=" in result
        assert "between(t,10.0,16.0)" in result

    def test_references_correct_input_indices(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=2,
            insertion_point_s=5.0,
            cutaway_duration_s=4.0,
        )
        assert "[2:v]" in result
        assert "[0:v]" in result
        assert "[broll2]" in result

    def test_includes_scale_to_1080x1920(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=0.0,
            cutaway_duration_s=5.0,
        )
        assert "scale=1080:1920" in result

    def test_includes_fade_in_and_out(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
            fade_duration=0.5,
        )
        assert "fade=t=in" in result
        assert "fade=t=out" in result

    def test_output_label_is_v(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=0.0,
            cutaway_duration_s=5.0,
        )
        assert result.endswith("[v]")


class TestAssembleWithBroll:
    """Tests for assemble_with_broll method."""

    async def test_empty_placements_delegates_to_assemble(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        assembler = ReelAssembler()
        manifest = CutawayManifest(clips=())
        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output) as mock_assemble:
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest)
            mock_assemble.assert_called_once_with([seg], output, transitions=None)
            assert result == output

    async def test_missing_clip_file_falls_back(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(tmp_path / "nonexistent.mp4"))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()
        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output) as mock_assemble:
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest)
            mock_assemble.assert_called_once()
            assert result == output

    async def test_valid_broll_calls_ffmpeg_with_filter(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg1.write_bytes(b"v1")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip), insertion_point_s=5.0, duration_s=4.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg1], output, manifest=manifest)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert "ffmpeg" in call_args
        assert "-filter_complex" in call_args

    async def test_cutaway_failure_falls_back_to_plain(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg1.write_bytes(b"v1")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip))

        # First call (cutaway) fails, second call (plain assemble) succeeds
        fail_proc = _mock_process(returncode=1, stderr=b"cutaway error")
        ok_proc = _mock_process(returncode=0)

        assembler = ReelAssembler()
        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(side_effect=[fail_proc, ok_proc])
            mock_aio.subprocess = __import__("asyncio").subprocess
            # The cutaway will fail, then it falls back to assemble() which
            # for a single segment just copies the file.
            # But the fallback assemble() does a shutil.copy, not ffmpeg, for 1 segment.
            # Let's use 2 segments to force ffmpeg calls.
            seg2 = tmp_path / "seg2.mp4"
            seg2.write_bytes(b"v2")
            manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
            result = await assembler.assemble_with_broll([seg1, seg2], output, manifest=manifest)
            assert result == output

    async def test_passes_transitions_on_fallback(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        transitions = (TransitionSpec(offset_seconds=10.0),)
        manifest = CutawayManifest(clips=())

        assembler = ReelAssembler()
        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output) as mock_assemble:
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest, transitions=transitions)
            mock_assemble.assert_called_once_with([seg], output, transitions=transitions)
            assert result == output
