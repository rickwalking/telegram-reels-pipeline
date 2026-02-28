"""Tests for ReelAssembler B-roll — two-pass assembly with _overlay_broll."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.domain.models import BrollPlacement, ClipSource, CutawayClip, CutawayManifest
from pipeline.infrastructure.adapters.reel_assembler import (
    AssemblyError,
    BrollReportEntry,
    BrollSummary,
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


def _make_cutaway_clip(
    source: ClipSource = ClipSource.VEO3,
    variant: str = "broll",
    clip_path: str = "/tmp/clip.mp4",
    insertion_point_s: float = 10.0,
    duration_s: float = 6.0,
    narrative_anchor: str = "test anchor",
    match_confidence: float = 0.8,
) -> CutawayClip:
    return CutawayClip(
        source=source,
        variant=variant,
        clip_path=clip_path,
        insertion_point_s=insertion_point_s,
        duration_s=duration_s,
        narrative_anchor=narrative_anchor,
        match_confidence=match_confidence,
    )


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

    async def test_valid_broll_invokes_two_pass(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg1.write_bytes(b"v1")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip), insertion_point_s=5.0, duration_s=4.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)
            ) as mock_res,
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base) as mock_p1,
            patch.object(
                assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output
            ) as mock_p2,
        ):
            base.write_bytes(b"base")
            result = await assembler.assemble_with_broll([seg1], output, manifest=manifest)
            assert result == output
            mock_res.assert_called_once()
            mock_p1.assert_called_once()
            mock_p2.assert_called_once()

    async def test_overlay_failure_falls_back_to_base_reel(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg1.write_bytes(b"v1")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(
                assembler, "_overlay_broll", new_callable=AsyncMock,
                side_effect=AssemblyError("overlay failed"),
            ),
        ):
            base.write_bytes(b"base")
            result = await assembler.assemble_with_broll([seg1], output, manifest=manifest)
            assert result == output
            assert output.exists()

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


class TestOverlayBroll:
    """Tests for _overlay_broll — FFmpeg PTS-offset overlay filter graph."""

    async def test_builds_correct_ffmpeg_command_single_clip(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        placement = _make_placement(clip_path="/tmp/clip1.mp4", insertion_point_s=5.0, duration_s=4.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            result = await assembler._overlay_broll(base, [placement], output)

        assert result == output
        call_args = mock_aio.create_subprocess_exec.call_args[0]
        assert call_args[0] == "ffmpeg"
        assert "-filter_complex" in call_args

        # Extract filter_complex argument
        fc_idx = list(call_args).index("-filter_complex")
        filter_graph = call_args[fc_idx + 1]

        # Verify setpts with PTS-offset for clip at insertion_point 5.0
        assert "setpts=PTS-STARTPTS+5.0/TB" in filter_graph
        assert "overlay=eof_action=pass" in filter_graph

    async def test_builds_correct_filter_two_clips(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        p1 = _make_placement(clip_path="/tmp/clip1.mp4", insertion_point_s=5.0, duration_s=4.0)
        p2 = _make_placement(clip_path="/tmp/clip2.mp4", insertion_point_s=20.0, duration_s=3.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [p1, p2], output)

        call_args = mock_aio.create_subprocess_exec.call_args[0]
        fc_idx = list(call_args).index("-filter_complex")
        filter_graph = call_args[fc_idx + 1]

        # Two clip chains with setpts
        assert "setpts=PTS-STARTPTS+5.0/TB[clip1]" in filter_graph
        assert "setpts=PTS-STARTPTS+20.0/TB[clip2]" in filter_graph

        # Chained overlays — first produces [v1], second produces [vout]
        assert "[0:v][clip1]overlay=eof_action=pass[v1]" in filter_graph
        assert "[v1][clip2]overlay=eof_action=pass[vout]" in filter_graph

    async def test_maps_base_audio(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        placement = _make_placement(clip_path="/tmp/clip1.mp4")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        map_indices = [i for i, a in enumerate(call_args) if a == "-map"]
        mapped_streams = {call_args[i + 1] for i in map_indices}
        assert "[vout]" in mapped_streams
        assert "0:a" in mapped_streams

    async def test_encoding_params(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        placement = _make_placement(clip_path="/tmp/clip1.mp4")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output)

        call_args = list(mock_aio.create_subprocess_exec.call_args[0])
        assert "-pix_fmt" in call_args
        assert "yuv420p" in call_args
        assert "-movflags" in call_args
        assert "+faststart" in call_args
        assert "-b:a" in call_args
        assert "128k" in call_args

    async def test_ffmpeg_failure_raises_assembly_error(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        placement = _make_placement(clip_path="/tmp/clip1.mp4")

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                return_value=_mock_process(returncode=1, stderr=b"overlay error")
            )
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            with pytest.raises(AssemblyError, match="FFmpeg B-roll overlay failed"):
                await assembler._overlay_broll(base, [placement], output)

    async def test_empty_placements_raises(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base-video")
        output = tmp_path / "output.mp4"

        assembler = ReelAssembler()
        with pytest.raises(AssemblyError, match="placements must not be empty"):
            await assembler._overlay_broll(base, [], output)


class TestTwoPassFlow:
    """Tests for the two-pass assembly flow in assemble_with_broll."""

    async def test_two_pass_calls_assemble_then_overlay(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        tmp_base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))

        assembler = ReelAssembler()
        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=tmp_base) as mock_assemble,
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output) as mock_overlay,
        ):
            tmp_base.write_bytes(b"base")
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest)

        mock_assemble.assert_called_once_with([seg], tmp_base, transitions=None)
        mock_overlay.assert_called_once()
        assert result == output

    async def test_fallback_when_overlay_fails(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        tmp_base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))

        assembler = ReelAssembler()
        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=tmp_base) as mock_assemble,
            patch.object(
                assembler,
                "_overlay_broll",
                new_callable=AsyncMock,
                side_effect=AssemblyError("overlay failed"),
            ),
        ):
            tmp_base.write_bytes(b"base-reel-content")
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest)

        mock_assemble.assert_called_once()
        assert result == output
        assert output.read_bytes() == b"base-reel-content"
        assert not tmp_base.exists()

    async def test_temp_file_cleaned_on_success(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        tmp_base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))

        assembler = ReelAssembler()
        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=tmp_base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            tmp_base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        assert not tmp_base.exists()

    async def test_no_valid_placements_delegates_to_assemble(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(tmp_path / "missing.mp4"))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))

        assembler = ReelAssembler()
        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output) as mock_assemble:
            result = await assembler.assemble_with_broll([seg], output, manifest=manifest)
            mock_assemble.assert_called_once_with([seg], output, transitions=None)
            assert result == output

    async def test_two_pass_with_transitions(self, tmp_path: Path) -> None:
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        seg1.write_bytes(b"v1")
        seg2.write_bytes(b"v2")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll")
        output = tmp_path / "reel.mp4"
        tmp_base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        transitions = (TransitionSpec(offset_seconds=10.0),)

        assembler = ReelAssembler()
        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=tmp_base) as mock_assemble,
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            tmp_base.write_bytes(b"base")
            await assembler.assemble_with_broll(
                [seg1, seg2], output, manifest=manifest, transitions=transitions
            )

        mock_assemble.assert_called_once_with([seg1, seg2], tmp_base, transitions=transitions)


class TestBrollReportDataclasses:
    """Tests for BrollReportEntry and BrollSummary frozen dataclasses."""

    def test_broll_report_entry_construction(self) -> None:
        entry = BrollReportEntry(
            variant="broll",
            clip_path="/tmp/clip.mp4",
            insertion_point_s=10.0,
            duration_s=5.0,
            narrative_anchor="anchor text",
            source="veo3",
            original_resolution=(720, 1280),
            upscaled=True,
        )
        assert entry.variant == "broll"
        assert entry.clip_path == "/tmp/clip.mp4"
        assert entry.insertion_point_s == 10.0
        assert entry.duration_s == 5.0
        assert entry.narrative_anchor == "anchor text"
        assert entry.source == "veo3"
        assert entry.original_resolution == (720, 1280)
        assert entry.upscaled is True

    def test_broll_report_entry_frozen(self) -> None:
        entry = BrollReportEntry(
            variant="broll",
            clip_path="/tmp/clip.mp4",
            insertion_point_s=10.0,
            duration_s=5.0,
            narrative_anchor="anchor",
            source="veo3",
            original_resolution=(1080, 1920),
            upscaled=False,
        )
        with pytest.raises(AttributeError):
            entry.upscaled = True  # type: ignore[misc]

    def test_broll_summary_construction(self) -> None:
        summary = BrollSummary(
            clips_inserted=0,
            placements=(),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=0,
            pass_2_duration_ms=0,
        )
        assert summary.clips_inserted == 0
        assert summary.placements == ()
        assert summary.assembly_method == "two_pass_overlay"
        assert summary.pass_1_duration_ms == 0
        assert summary.pass_2_duration_ms == 0

    def test_broll_summary_frozen(self) -> None:
        summary = BrollSummary(
            clips_inserted=0,
            placements=(),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=0,
            pass_2_duration_ms=0,
        )
        with pytest.raises(AttributeError):
            summary.clips_inserted = 1  # type: ignore[misc]


class TestWriteBrollReport:
    """Tests for _write_broll_report atomic write."""

    def test_writes_report_json(self, tmp_path: Path) -> None:
        output = tmp_path / "final-reel.mp4"
        output.write_bytes(b"video")

        summary = BrollSummary(
            clips_inserted=1,
            placements=(
                BrollReportEntry(
                    variant="broll",
                    clip_path="/tmp/clip.mp4",
                    insertion_point_s=10.0,
                    duration_s=5.0,
                    narrative_anchor="anchor",
                    source="veo3",
                    original_resolution=(720, 1280),
                    upscaled=True,
                ),
            ),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=150,
            pass_2_duration_ms=300,
        )
        ReelAssembler._write_broll_report(output, summary)

        report_path = tmp_path / "assembly-report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        assert "broll_summary" in data
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 1
        assert bs["assembly_method"] == "two_pass_overlay"
        assert bs["pass_1_duration_ms"] == 150
        assert bs["pass_2_duration_ms"] == 300
        assert len(bs["placements"]) == 1

    def test_report_placement_fields(self, tmp_path: Path) -> None:
        output = tmp_path / "final-reel.mp4"
        output.write_bytes(b"video")

        entry = BrollReportEntry(
            variant="broll",
            clip_path="/workspace/clip.mp4",
            insertion_point_s=15.5,
            duration_s=6.0,
            narrative_anchor="the key moment",
            source="external",
            original_resolution=(540, 960),
            upscaled=True,
        )
        summary = BrollSummary(
            clips_inserted=1,
            placements=(entry,),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=100,
            pass_2_duration_ms=200,
        )
        ReelAssembler._write_broll_report(output, summary)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        p = data["broll_summary"]["placements"][0]
        assert p["variant"] == "broll"
        assert p["clip_path"] == "/workspace/clip.mp4"
        assert p["insertion_point_s"] == 15.5
        assert p["duration_s"] == 6.0
        assert p["narrative_anchor"] == "the key moment"
        assert p["source"] == "external"
        assert p["original_resolution"] == [540, 960]
        assert p["upscaled"] is True

    def test_zero_clip_report(self, tmp_path: Path) -> None:
        output = tmp_path / "final-reel.mp4"
        output.write_bytes(b"video")

        summary = BrollSummary(
            clips_inserted=0,
            placements=(),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=0,
            pass_2_duration_ms=0,
        )
        ReelAssembler._write_broll_report(output, summary)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 0
        assert bs["placements"] == []

    def test_atomic_write_no_partial_file(self, tmp_path: Path) -> None:
        """Report should not leave a partial file on write error."""
        output = tmp_path / "final-reel.mp4"
        output.write_bytes(b"video")

        summary = BrollSummary(
            clips_inserted=0,
            placements=(),
            assembly_method="two_pass_overlay",
            pass_1_duration_ms=0,
            pass_2_duration_ms=0,
        )

        report_path = tmp_path / "assembly-report.json"
        # Simulate os.replace failure
        with (
            patch("pipeline.infrastructure.adapters.reel_assembler.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            ReelAssembler._write_broll_report(output, summary)

        # Report file should NOT exist since atomic rename failed
        assert not report_path.exists()


class TestBrollReportIntegration:
    """Integration tests: assemble_with_broll writes assembly-report.json."""

    async def test_report_written_on_successful_two_pass(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip), insertion_point_s=5.0, duration_s=4.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(720, 1280)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock,
                return_value=Path(str(clip) + "_upscaled"),
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        report_path = tmp_path / "assembly-report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 1
        assert bs["assembly_method"] == "two_pass_overlay"
        assert bs["pass_1_duration_ms"] >= 0
        assert bs["pass_2_duration_ms"] >= 0
        assert len(bs["placements"]) == 1

        p = bs["placements"][0]
        assert p["variant"] == "broll"
        assert p["clip_path"] == str(clip)
        assert p["insertion_point_s"] == 5.0
        assert p["duration_s"] == 4.0
        assert p["narrative_anchor"] == "test anchor"
        assert p["source"] == "veo3"
        assert p["original_resolution"] == [720, 1280]
        assert p["upscaled"] is True

    async def test_report_written_on_empty_manifest(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        manifest = CutawayManifest(clips=())
        assembler = ReelAssembler()

        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output):
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        report_path = tmp_path / "assembly-report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 0
        assert bs["placements"] == []
        assert bs["assembly_method"] == "two_pass_overlay"
        assert bs["pass_1_duration_ms"] == 0
        assert bs["pass_2_duration_ms"] == 0

    async def test_report_written_on_all_clips_missing(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(tmp_path / "nonexistent.mp4"))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=output):
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        report_path = tmp_path / "assembly-report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 0
        assert bs["placements"] == []

    async def test_upscale_tracking_not_upscaled(self, tmp_path: Path) -> None:
        """Clip already at target resolution is reported as not upscaled."""
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip), insertion_point_s=5.0, duration_s=4.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock,
                return_value=Path(clip),  # Same path = not upscaled
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        p = data["broll_summary"]["placements"][0]
        assert p["original_resolution"] == [1080, 1920]
        assert p["upscaled"] is False

    async def test_upscale_tracking_was_upscaled(self, tmp_path: Path) -> None:
        """Clip below target resolution is reported as upscaled with original res."""
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip), insertion_point_s=5.0, duration_s=4.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        upscaled_path = tmp_path / "_upscaled_broll.mp4"
        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(540, 960)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock,
                return_value=upscaled_path,  # Different path = was upscaled
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        p = data["broll_summary"]["placements"][0]
        assert p["original_resolution"] == [540, 960]
        assert p["upscaled"] is True

    async def test_timing_instrumentation(self, tmp_path: Path) -> None:
        """Pass 1 and Pass 2 timing values are non-negative integers."""
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        placement = _make_placement(clip_path=str(clip))
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(placement,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        bs = data["broll_summary"]
        assert isinstance(bs["pass_1_duration_ms"], int)
        assert isinstance(bs["pass_2_duration_ms"], int)
        assert bs["pass_1_duration_ms"] >= 0
        assert bs["pass_2_duration_ms"] >= 0

    async def test_report_source_from_cutaway_clip(self, tmp_path: Path) -> None:
        """Report source field comes from CutawayClip.source, not a default."""
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "ext_clip.mp4"
        clip.write_bytes(b"ext-video")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        # Build a manifest with an external source clip directly
        ext_clip = _make_cutaway_clip(
            source=ClipSource.EXTERNAL,
            clip_path=str(clip),
            insertion_point_s=8.0,
            duration_s=5.0,
            narrative_anchor="external moment",
        )
        manifest = CutawayManifest(clips=(ext_clip,))
        assembler = ReelAssembler()

        with (
            patch.object(
                assembler, "_probe_resolution", new_callable=AsyncMock, return_value=(1080, 1920)
            ),
            patch.object(
                assembler, "_ensure_clip_resolution", new_callable=AsyncMock, return_value=Path(clip)
            ),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        p = data["broll_summary"]["placements"][0]
        assert p["source"] == "external"

    async def test_multiple_clips_report(self, tmp_path: Path) -> None:
        """Report includes all clips with correct metadata."""
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip1 = tmp_path / "clip1.mp4"
        clip1.write_bytes(b"clip1")
        clip2 = tmp_path / "clip2.mp4"
        clip2.write_bytes(b"clip2")
        output = tmp_path / "reel.mp4"
        base = output.with_suffix(".base.mp4")

        p1 = _make_placement(clip_path=str(clip1), insertion_point_s=5.0, duration_s=4.0)
        p2 = _make_placement(clip_path=str(clip2), insertion_point_s=20.0, duration_s=3.0)
        manifest, _ = CutawayManifest.from_broll_and_external(broll=(p1, p2))
        assembler = ReelAssembler()

        # First clip not upscaled (1080x1920), second upscaled (540x960)
        resolutions = [(1080, 1920), (540, 960)]
        probe_call_count = 0

        async def mock_probe(clip_path: Path) -> tuple[int, int]:
            nonlocal probe_call_count
            result = resolutions[probe_call_count]
            probe_call_count += 1
            return result

        ensure_call_count = 0

        async def mock_ensure(clip_path: Path, temp_dir: Path) -> Path:
            nonlocal ensure_call_count
            idx = ensure_call_count
            ensure_call_count += 1
            if idx == 0:
                return clip_path  # Not upscaled
            return temp_dir / f"_upscaled_{clip_path.stem}.mp4"  # Upscaled

        with (
            patch.object(assembler, "_probe_resolution", side_effect=mock_probe),
            patch.object(assembler, "_ensure_clip_resolution", side_effect=mock_ensure),
            patch.object(assembler, "assemble", new_callable=AsyncMock, return_value=base),
            patch.object(assembler, "_overlay_broll", new_callable=AsyncMock, return_value=output),
        ):
            base.write_bytes(b"base")
            await assembler.assemble_with_broll([seg], output, manifest=manifest)

        data = json.loads((tmp_path / "assembly-report.json").read_text())
        bs = data["broll_summary"]
        assert bs["clips_inserted"] == 2
        assert len(bs["placements"]) == 2

        # First clip: not upscaled
        assert bs["placements"][0]["original_resolution"] == [1080, 1920]
        assert bs["placements"][0]["upscaled"] is False
        assert bs["placements"][0]["insertion_point_s"] == 5.0

        # Second clip: upscaled
        assert bs["placements"][1]["original_resolution"] == [540, 960]
        assert bs["placements"][1]["upscaled"] is True
        assert bs["placements"][1]["insertion_point_s"] == 20.0
