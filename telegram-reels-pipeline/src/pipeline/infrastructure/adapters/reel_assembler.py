"""Reel assembler — concatenate encoded video segments into a final reel."""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from pipeline.domain.errors import PipelineError

logger = logging.getLogger(__name__)

# Default xfade transition duration in seconds
_XFADE_DURATION: float = 0.5


@dataclass(frozen=True)
class TransitionSpec:
    """Specification for a transition between two segments."""

    offset_seconds: float
    effect: str = "fade"
    duration: float = _XFADE_DURATION


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
