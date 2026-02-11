"""Reel assembler — concatenate encoded video segments into a final reel."""

from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from pipeline.domain.errors import PipelineError

logger = logging.getLogger(__name__)


class AssemblyError(PipelineError):
    """Failed to assemble reel from segments."""


class ReelAssembler:
    """Concatenate encoded video segments into a single output file via FFmpeg."""

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg concat demuxer (single quotes -> '\\''). """
        escaped = str(path.resolve()).replace("'", "'\\''")
        return f"file '{escaped}'"

    async def assemble(self, segments: list[Path], output: Path) -> Path:
        """Concatenate video segments into a single reel.

        For a single segment, performs a file copy. For multiple segments,
        uses FFmpeg concat demuxer with stream copy (no re-encoding).
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

        list_file = output.parent / f"_assembly_{output.stem}.txt"
        list_file.write_text(
            "\n".join(self._escape_concat_path(seg) for seg in segments)
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
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

        logger.info("Assembled %d segments into %s", len(segments), output.name)
        return output

    async def validate_duration(
        self, reel: Path, min_duration: float = 30.0, max_duration: float = 120.0,
    ) -> bool:
        """Validate the assembled reel meets duration requirements via ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
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
