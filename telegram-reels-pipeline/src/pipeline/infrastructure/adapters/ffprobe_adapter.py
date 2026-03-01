"""FfprobeAdapter — async ffprobe wrapper implementing ClipDurationProber protocol."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.cli.protocols import ClipDurationProber

logger = logging.getLogger(__name__)

_FFPROBE_TIMEOUT_S = 30


class FfprobeAdapter:
    """Probe video clip duration via ffprobe subprocess.

    Satisfies the ClipDurationProber protocol. Returns None on any
    failure (non-zero exit, parse error, timeout, missing binary).
    """

    if TYPE_CHECKING:
        _protocol_check: ClipDurationProber

    async def probe(self, clip_path: Path) -> float | None:
        """Return duration in seconds, or None on failure."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(clip_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=_FFPROBE_TIMEOUT_S)
            if proc.returncode != 0:
                logger.debug("ffprobe returned non-zero exit code %d for %s", proc.returncode, clip_path)
                return None
            return float(stdout.decode().strip())
        except TimeoutError:
            logger.warning("ffprobe timed out for %s", clip_path)
            return None
        except (OSError, ValueError) as exc:
            logger.debug("ffprobe failed for %s: %s", clip_path, exc)
            return None
