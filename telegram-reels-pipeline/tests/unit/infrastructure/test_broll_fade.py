"""Tests for B-roll alpha fade transitions in cutaway overlay filters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.domain.models import BrollPlacement
from pipeline.infrastructure.adapters.reel_assembler import ReelAssembler


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


def _extract_filter_complex(call_args: tuple[object, ...]) -> str:
    """Extract the -filter_complex value from an FFmpeg call args tuple."""
    args = list(call_args)
    idx = args.index("-filter_complex")
    return str(args[idx + 1])


class TestBrollFadeBuildCutawayFilter:
    """Tests for alpha fade filters in _build_cutaway_filter."""

    def test_contains_yuva420p_format(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
        )
        assert "format=yuva420p" in result

    def test_standard_clip_fade_in(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
            fade_duration=0.5,
        )
        assert "fade=t=in:st=0:d=0.5:alpha=1" in result

    def test_standard_clip_fade_out(self) -> None:
        # fade_out_start = 6.0 - 0.5 = 5.5
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
            fade_duration=0.5,
        )
        assert "fade=t=out:st=5.5:d=0.5:alpha=1" in result

    def test_short_clip_clamps_fade(self) -> None:
        # 0.8s clip: eff_fade = min(0.5, 0.8*0.4) = 0.32
        # fade_out_start = 0.8 - 0.32 = 0.48
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=5.0,
            cutaway_duration_s=0.8,
            fade_duration=0.5,
        )
        assert "fade=t=in:st=0:d=0.32:alpha=1" in result
        assert "fade=t=out:st=0.48" in result
        assert "d=0.32:alpha=1" in result

    def test_custom_fade_duration(self) -> None:
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
            fade_duration=0.3,
        )
        # eff_fade = min(0.3, 6.0*0.4) = 0.3
        # fade_out_start = 6.0 - 0.3 = 5.7
        assert "fade=t=in:st=0:d=0.3:alpha=1" in result
        assert "fade=t=out:st=5.7:d=0.3:alpha=1" in result

    def test_fade_before_setpts_in_cutaway_filter(self) -> None:
        """Fade filters must appear in the chain (after scale/format, before overlay)."""
        result = ReelAssembler._build_cutaway_filter(
            base_segment_index=0,
            broll_input_index=1,
            insertion_point_s=10.0,
            cutaway_duration_s=6.0,
        )
        # The filter chain should be: setpts -> scale -> format -> fade_in -> fade_out -> [label]; overlay
        format_pos = result.index("format=yuva420p")
        fade_in_pos = result.index("fade=t=in")
        fade_out_pos = result.index("fade=t=out")
        overlay_pos = result.index("overlay=")
        assert format_pos < fade_in_pos < fade_out_pos < overlay_pos


class TestBrollFadeInCutawayAssembly:
    """Tests for alpha fade in the full _assemble_with_cutaways pipeline."""

    async def test_filter_graph_contains_yuva420p(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip), duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "format=yuva420p" in filter_graph

    async def test_standard_clip_fade_values(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip), duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "fade=t=in:st=0:d=0.5:alpha=1" in filter_graph
        assert "fade=t=out:st=5.5:d=0.5:alpha=1" in filter_graph

    async def test_short_clip_effective_fade_clamped(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        # 0.8s clip: eff_fade = min(0.5, 0.8*0.4) = 0.32
        placement = _make_placement(clip_path=str(clip), duration_s=0.8)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        # eff_fade = min(0.5, 0.8*0.4) = 0.32
        assert "d=0.32" in filter_graph
        # fade_out_start = 0.8 - 0.32 = 0.48
        assert "fade=t=out:st=0.48" in filter_graph

    async def test_custom_fade_duration_propagates(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip), duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,), fade_duration=0.3)

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        # eff_fade = min(0.3, 6.0*0.4) = 0.3
        assert "fade=t=in:st=0:d=0.3:alpha=1" in filter_graph
        # fade_out_start = 6.0 - 0.3 = 5.7
        assert "fade=t=out:st=5.7:d=0.3:alpha=1" in filter_graph

    async def test_fade_appears_before_overlay_in_filter(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"broll-video")
        output = tmp_path / "reel.mp4"

        placement = _make_placement(clip_path=str(clip), duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(placement,))

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        format_pos = filter_graph.index("format=yuva420p")
        fade_in_pos = filter_graph.index("fade=t=in")
        fade_out_pos = filter_graph.index("fade=t=out")
        overlay_pos = filter_graph.index("overlay=")
        assert format_pos < fade_in_pos < fade_out_pos < overlay_pos

    async def test_multiple_broll_clips_each_get_fade(self, tmp_path: Path) -> None:
        seg = tmp_path / "seg.mp4"
        seg.write_bytes(b"video")
        clip1 = tmp_path / "broll1.mp4"
        clip1.write_bytes(b"broll1")
        clip2 = tmp_path / "broll2.mp4"
        clip2.write_bytes(b"broll2")
        output = tmp_path / "reel.mp4"

        bp1 = _make_placement(clip_path=str(clip1), insertion_point_s=5.0, duration_s=4.0)
        bp2 = _make_placement(clip_path=str(clip2), insertion_point_s=15.0, duration_s=3.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler.assemble_with_broll([seg], output, broll_placements=(bp1, bp2))

        filter_graph = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        # Both clips should have yuva420p format and fade filters
        assert filter_graph.count("format=yuva420p") == 2
        assert filter_graph.count("fade=t=in") == 2
        assert filter_graph.count("fade=t=out") == 2
