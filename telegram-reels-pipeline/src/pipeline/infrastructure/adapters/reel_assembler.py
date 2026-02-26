"""Reel assembler — concatenate encoded video segments into a final reel."""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from pipeline.domain.enums import TransitionKind
from pipeline.domain.errors import PipelineError
from pipeline.domain.models import BrollPlacement

logger = logging.getLogger(__name__)

# Default xfade transition durations in seconds
_STYLE_CHANGE_DURATION: float = 0.5
_NARRATIVE_BOUNDARY_DURATION: float = 1.0

# Default effect for narrative boundary transitions
_NARRATIVE_BOUNDARY_EFFECT: str = "dissolve"


@dataclass(frozen=True)
class TransitionSpec:
    """Specification for a transition between two segments."""

    offset_seconds: float
    effect: str = "fade"
    duration: float = _STYLE_CHANGE_DURATION
    kind: TransitionKind = TransitionKind.STYLE_CHANGE


def make_transition(
    offset_seconds: float,
    kind: TransitionKind = TransitionKind.STYLE_CHANGE,
    effect: str | None = None,
) -> TransitionSpec:
    """Create a TransitionSpec with sensible defaults based on kind.

    Narrative boundaries get dissolve (1.0s). Style changes get slide/wipe (0.5s).
    """
    if kind == TransitionKind.NARRATIVE_BOUNDARY:
        return TransitionSpec(
            offset_seconds=offset_seconds,
            effect=effect or _NARRATIVE_BOUNDARY_EFFECT,
            duration=_NARRATIVE_BOUNDARY_DURATION,
            kind=kind,
        )
    return TransitionSpec(
        offset_seconds=offset_seconds,
        effect=effect or "fade",
        duration=_STYLE_CHANGE_DURATION,
        kind=kind,
    )


class AssemblyError(PipelineError):
    """Failed to assemble reel from segments."""


class ReelAssembler:
    """Concatenate encoded video segments into a single output file via FFmpeg."""

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg concat demuxer (single quotes -> '\\'')."""
        escaped = str(path.resolve()).replace("'", "'\\''")
        return f"file '{escaped}'"

    @staticmethod
    def _build_xfade_filter(
        segment_count: int,
        transitions: tuple[TransitionSpec, ...],
    ) -> str:
        """Build an xfade filter_complex graph for N segments with transition specs.

        Builds parallel video (xfade) and audio (acrossfade) chains.
        Video: [0:v][1:v]xfade -> [tmp1][2:v]xfade -> ... -> [v]
        Audio: [0:a][1:a]acrossfade -> [atmp1][2:a]acrossfade -> ... -> [a]
        """
        if len(transitions) != segment_count - 1:
            raise AssemblyError(f"Expected {segment_count - 1} transitions, got {len(transitions)}")

        video_parts: list[str] = []
        audio_parts: list[str] = []
        for i, tr in enumerate(transitions):
            # Video chain
            v_src = "[0:v][1:v]" if i == 0 else f"[vtmp{i}][{i + 1}:v]"
            v_out = "[v]" if i == len(transitions) - 1 else f"[vtmp{i + 1}]"
            video_parts.append(
                f"{v_src}xfade=transition={tr.effect}:duration={tr.duration}:offset={tr.offset_seconds}{v_out}"
            )
            # Audio chain
            a_src = "[0:a][1:a]" if i == 0 else f"[atmp{i}][{i + 1}:a]"
            a_out = "[a]" if i == len(transitions) - 1 else f"[atmp{i + 1}]"
            audio_parts.append(f"{a_src}acrossfade=d={tr.duration}{a_out}")

        return ";".join(video_parts + audio_parts)

    async def assemble(
        self,
        segments: list[Path],
        output: Path,
        *,
        transitions: tuple[TransitionSpec, ...] | None = None,
    ) -> Path:
        """Concatenate video segments into a single reel.

        For a single segment, performs a file copy. For multiple segments
        without transitions, uses FFmpeg concat demuxer with stream copy
        (no re-encoding). When transitions are provided, uses xfade
        filter_complex (requires re-encoding at boundaries).
        """
        if not segments:
            raise AssemblyError("segments must not be empty")

        for seg in segments:
            if not seg.exists():
                raise AssemblyError(f"Segment file not found: {seg}")

        output.parent.mkdir(parents=True, exist_ok=True)

        if len(segments) == 1:
            shutil.copy2(segments[0], output)
            return output

        if transitions:
            try:
                return await self._assemble_xfade(segments, output, transitions)
            except AssemblyError:
                logger.warning("xfade assembly failed, falling back to concat")
                return await self._assemble_concat(segments, output)

        return await self._assemble_concat(segments, output)

    async def _assemble_concat(self, segments: list[Path], output: Path) -> Path:
        """Assemble via concat demuxer with stream copy (no re-encoding)."""
        list_file = output.parent / f"_assembly_{output.stem}.txt"
        list_file.write_text("\n".join(self._escape_concat_path(seg) for seg in segments))

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-y",
                str(output),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise AssemblyError(f"FFmpeg concat failed (exit {proc.returncode}): {stderr.decode()}")
        finally:
            list_file.unlink(missing_ok=True)

        logger.info("Assembled %d segments (concat) into %s", len(segments), output.name)
        return output

    async def _assemble_xfade(
        self,
        segments: list[Path],
        output: Path,
        transitions: tuple[TransitionSpec, ...],
    ) -> Path:
        """Assemble via xfade filter_complex (re-encodes at transition boundaries)."""
        filter_graph = self._build_xfade_filter(len(segments), transitions)

        cmd: list[str] = ["ffmpeg"]
        for seg in segments:
            cmd.extend(["-i", str(seg)])
        cmd.extend(
            [
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                "-y",
                str(output),
            ]
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AssemblyError(f"FFmpeg xfade failed (exit {proc.returncode}): {stderr.decode()}")

        logger.info("Assembled %d segments (xfade) into %s", len(segments), output.name)
        return output

    async def _overlay_broll(
        self,
        base_reel: Path,
        placements: list[BrollPlacement],
        output: Path,
    ) -> Path:
        """Overlay B-roll clips onto an already-assembled base reel.

        Builds a PTS-offset filter graph where each B-roll clip is time-shifted
        to its insertion point and chained via ``overlay=eof_action=pass``.
        Audio comes exclusively from the base reel.
        """
        if not placements:
            raise AssemblyError("placements must not be empty for overlay")

        output.parent.mkdir(parents=True, exist_ok=True)

        # Build inputs: base reel first, then each B-roll clip
        cmd: list[str] = ["ffmpeg", "-i", str(base_reel)]
        for bp in placements:
            cmd.extend(["-i", bp.clip_path])

        # Build filter graph
        filter_parts: list[str] = []
        for i, bp in enumerate(placements):
            clip_idx = i + 1  # 0 is base reel
            filter_parts.append(f"[{clip_idx}:v]setpts=PTS-STARTPTS+{bp.insertion_point_s}/TB[clip{clip_idx}]")

        # Chain overlays: [0:v][clip1]overlay -> [v1]; [v1][clip2]overlay -> [v2]; ...
        current_label = "[0:v]"
        for i in range(len(placements)):
            clip_idx = i + 1
            is_last = i == len(placements) - 1
            out_label = "[vout]" if is_last else f"[v{clip_idx}]"
            filter_parts.append(f"{current_label}[clip{clip_idx}]overlay=eof_action=pass{out_label}")
            current_label = out_label

        filter_graph = ";".join(filter_parts)

        cmd.extend(
            [
                "-filter_complex",
                filter_graph,
                "-map",
                "[vout]",
                "-map",
                "0:a",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-y",
                str(output),
            ]
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AssemblyError(f"FFmpeg B-roll overlay failed (exit {proc.returncode}): {stderr.decode()}")

        logger.info("Overlaid %d B-roll clips onto base reel -> %s", len(placements), output.name)
        return output

    async def assemble_with_broll(
        self,
        segments: list[Path],
        output: Path,
        broll_placements: tuple[BrollPlacement, ...],
        transitions: tuple[TransitionSpec, ...] | None = None,
    ) -> Path:
        """Two-pass assembly: base reel first, then B-roll overlay.

        **Pass 1** — assemble segments (with optional xfade transitions)
        into a temporary base reel via :meth:`assemble`.

        **Pass 2** — overlay validated B-roll clips on the base reel via
        :meth:`_overlay_broll` using PTS-offset ``overlay=eof_action=pass``.

        Falls back to the base reel (no B-roll) when Pass 2 fails.
        """
        if not broll_placements:
            return await self.assemble(segments, output, transitions=transitions)

        # Validate clip files exist — skip missing ones gracefully
        valid_placements: list[BrollPlacement] = []
        for bp in broll_placements:
            clip = Path(bp.clip_path)
            if clip.exists():
                valid_placements.append(bp)
            else:
                logger.warning("B-roll clip not found, skipping: %s", bp.clip_path)

        if not valid_placements:
            logger.warning("No valid B-roll clips found — assembling without B-roll")
            return await self.assemble(segments, output, transitions=transitions)

        # Pass 1: assemble base reel into a temp file
        tmp_path = output.with_suffix(".base.mp4")
        await self.assemble(segments, tmp_path, transitions=transitions)
        logger.info("Pass 1 complete: base reel at %s", tmp_path.name)

        # Pass 2: overlay B-roll clips onto the base reel
        try:
            result = await self._overlay_broll(tmp_path, valid_placements, output)
            tmp_path.unlink(missing_ok=True)
            logger.info("Pass 2 complete: B-roll overlay at %s", output.name)
            return result
        except AssemblyError as exc:
            logger.warning("B-roll overlay failed (%s), falling back to base reel", exc.message)
            shutil.move(str(tmp_path), str(output))
            return output

    async def validate_duration(
        self,
        reel: Path,
        min_duration: float = 30.0,
        max_duration: float = 120.0,
    ) -> bool:
        """Validate the assembled reel meets duration requirements via ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(reel),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffprobe failed: %s", stderr.decode())
            return False

        try:
            duration = float(stdout.decode().strip())
        except ValueError:
            return False

        return min_duration <= duration <= max_duration
