"""Tests for B-roll alpha fade transitions in _overlay_broll."""

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


class TestOverlayBrollFade:
    """Tests for alpha fade filters in _overlay_broll filter graph."""

    async def test_contains_yuva420p_format(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "format=yuva420p" in fg

    async def test_standard_clip_fade_in(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output, fade_duration=0.5)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "fade=t=in:st=0:d=0.5:alpha=1" in fg

    async def test_standard_clip_fade_out(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        # fade_out_start = 6.0 - 0.5 = 5.5
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output, fade_duration=0.5)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "fade=t=out:st=5.5:d=0.5:alpha=1" in fg

    async def test_short_clip_clamps_fade(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        # 0.8s clip: eff_fade = min(0.5, 0.8*0.4) = 0.32
        # fade_out_start = 0.8 - 0.32 = 0.48
        placement = _make_placement(duration_s=0.8)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output, fade_duration=0.5)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "d=0.32" in fg
        assert "fade=t=out:st=0.48" in fg
        assert "d=0.32:alpha=1" in fg

    async def test_custom_fade_duration(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output, fade_duration=0.3)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        # eff_fade = min(0.3, 6.0*0.4) = 0.3
        assert "fade=t=in:st=0:d=0.3:alpha=1" in fg
        # fade_out_start = 6.0 - 0.3 = 5.7
        assert "fade=t=out:st=5.7:d=0.3:alpha=1" in fg

    async def test_fade_ordering_in_filter_chain(self, tmp_path: Path) -> None:
        """format -> fade_in -> fade_out -> setpts must precede overlay."""
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [placement], output)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        format_pos = fg.index("format=yuva420p")
        fade_in_pos = fg.index("fade=t=in")
        fade_out_pos = fg.index("fade=t=out")
        overlay_pos = fg.index("overlay=")
        assert format_pos < fade_in_pos < fade_out_pos < overlay_pos

    async def test_multiple_clips_each_get_fade(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        bp1 = _make_placement(clip_path="/tmp/clip1.mp4", insertion_point_s=5.0, duration_s=4.0)
        bp2 = _make_placement(clip_path="/tmp/clip2.mp4", insertion_point_s=15.0, duration_s=3.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            await assembler._overlay_broll(base, [bp1, bp2], output)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert fg.count("format=yuva420p") == 2
        assert fg.count("fade=t=in") == 2
        assert fg.count("fade=t=out") == 2

    async def test_default_fade_duration_is_half_second(self, tmp_path: Path) -> None:
        base = tmp_path / "base.mp4"
        base.write_bytes(b"base")
        output = tmp_path / "output.mp4"
        placement = _make_placement(duration_s=6.0)

        with patch("pipeline.infrastructure.adapters.reel_assembler.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            assembler = ReelAssembler()
            # No explicit fade_duration — should default to 0.5
            await assembler._overlay_broll(base, [placement], output)

        fg = _extract_filter_complex(mock_aio.create_subprocess_exec.call_args[0])
        assert "fade=t=in:st=0:d=0.5:alpha=1" in fg
        assert "fade=t=out:st=5.5:d=0.5:alpha=1" in fg
