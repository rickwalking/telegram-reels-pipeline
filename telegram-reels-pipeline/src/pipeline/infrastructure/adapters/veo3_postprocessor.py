"""Veo3PostProcessor — crop watermark and validate Veo3-generated clips."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

from pipeline.domain.errors import PipelineError

logger = logging.getLogger(__name__)

# Expected 9:16 aspect ratio (width / height = 9/16 = 0.5625)
_EXPECTED_ASPECT_RATIO: float = 9.0 / 16.0
_ASPECT_RATIO_TOLERANCE: float = 0.01

# Duration tolerance in seconds
_DURATION_TOLERANCE_S: float = 1.0

# Black-frame detection parameters
_BLACKDETECT_MIN_DURATION: float = 0.5
_BLACKDETECT_PIX_TH: float = 0.10


class Veo3PostProcessError(PipelineError):
    """Veo3 clip post-processing or validation failure."""


class Veo3PostProcessor:
    """Crops watermark and validates Veo3-generated clips before assembly.

    Applies a bottom-strip crop to remove the Veo3 watermark, performs an
    atomic write (tmp file then rename), then validates the result for:
      - 9:16 aspect ratio (tolerance ±0.01)
      - Duration within ±1s of expected
      - No long black-frame sequences (≥0.5s at 10% pixel threshold)
    """

    def __init__(self, crop_bottom_px: int = 16) -> None:
        self._crop_bottom_px = crop_bottom_px

    def build_crop_filter(self) -> str:
        """Return the FFmpeg video filter string for bottom strip crop."""
        return f"crop=in_w:in_h-{self._crop_bottom_px}:0:0"

    async def crop_and_validate(
        self,
        clip_path: Path,
        expected_duration_s: int,
    ) -> bool:
        """Crop watermark and validate clip quality.

        Steps:
          1. Probe resolution and duration with ffprobe.
          2. Crop bottom strip with FFmpeg, writing atomically via a .tmp.mp4
             file renamed to the original path on success.
          3. Validate: 9:16 aspect ratio, duration within ±1s, no black frames.

        Returns True if the clip passes all checks; False on any failure
        (with a warning logged but no exception raised to the caller).
        """
        if not clip_path.exists():
            logger.warning("Veo3 clip not found: %s", clip_path)
            return False

        # --- Step 1: probe original clip ---
        try:
            width, height, duration = await self._probe_clip(clip_path)
        except Veo3PostProcessError as exc:
            logger.warning("ffprobe failed for %s: %s", clip_path.name, exc)
            return False

        # --- Step 2: crop watermark (atomic write) ---
        tmp_path = clip_path.with_suffix(".tmp.mp4")
        try:
            await self._run_crop(clip_path, tmp_path)
        except Veo3PostProcessError as exc:
            logger.warning("FFmpeg crop failed for %s: %s", clip_path.name, exc)
            tmp_path.unlink(missing_ok=True)
            return False

        try:
            tmp_path.replace(clip_path)
        except OSError as exc:
            logger.warning("Atomic rename failed for %s: %s", clip_path.name, exc)
            tmp_path.unlink(missing_ok=True)
            return False

        # Recompute height after crop for aspect-ratio check.
        cropped_height = height - self._crop_bottom_px

        # --- Step 3: validate ---
        if not self._check_aspect_ratio(width, cropped_height):
            logger.warning(
                "Veo3 clip %s failed aspect-ratio check: %dx%d (ratio %.4f, expected %.4f ±%.2f)",
                clip_path.name,
                width,
                cropped_height,
                width / cropped_height if cropped_height else 0,
                _EXPECTED_ASPECT_RATIO,
                _ASPECT_RATIO_TOLERANCE,
            )
            return False

        if not self._check_duration(duration, expected_duration_s):
            logger.warning(
                "Veo3 clip %s failed duration check: %.2fs (expected %ds ±%.0fs)",
                clip_path.name,
                duration,
                expected_duration_s,
                _DURATION_TOLERANCE_S,
            )
            return False

        has_black = await self._detect_black_frames(clip_path)
        if has_black:
            logger.warning("Veo3 clip %s contains black-frame sequences", clip_path.name)
            return False

        logger.info(
            "Veo3 clip %s passed post-processing (%dx%d, %.2fs)",
            clip_path.name,
            width,
            cropped_height,
            duration,
        )
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _probe_clip(self, clip_path: Path) -> tuple[int, int, float]:
        """Run ffprobe and return (width, height, duration).

        Raises Veo3PostProcessError on subprocess failure or parse error.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,duration",
            "-of",
            "json",
            str(clip_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Veo3PostProcessError(
                f"ffprobe exited {proc.returncode}: {stderr.decode()}"
            )

        try:
            data = json.loads(stdout.decode())
            streams = data.get("streams", [])
            if not streams:
                raise Veo3PostProcessError("ffprobe returned no video streams")
            stream = streams[0]
            width = int(stream["width"])
            height = int(stream["height"])
            duration = float(stream["duration"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise Veo3PostProcessError(
                f"Could not parse ffprobe output: {exc}"
            ) from exc

        return width, height, duration

    async def _run_crop(self, input_path: Path, output_path: Path) -> None:
        """Run FFmpeg to crop the bottom strip, writing to output_path.

        Raises Veo3PostProcessError on subprocess failure.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(input_path),
            "-vf",
            self.build_crop_filter(),
            "-c:a",
            "copy",
            "-y",
            str(output_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Veo3PostProcessError(
                f"FFmpeg crop exited {proc.returncode}: {stderr.decode()}"
            )

    @staticmethod
    def _check_aspect_ratio(width: int, height: int) -> bool:
        """Return True if width/height is within tolerance of 9:16."""
        if height <= 0:
            return False
        ratio = width / height
        return abs(ratio - _EXPECTED_ASPECT_RATIO) <= _ASPECT_RATIO_TOLERANCE

    @staticmethod
    def _check_duration(actual: float, expected_s: int) -> bool:
        """Return True if actual duration is within ±1s of expected."""
        return abs(actual - expected_s) <= _DURATION_TOLERANCE_S

    async def _detect_black_frames(self, clip_path: Path) -> bool:
        """Return True if any black-frame sequence is found.

        Runs FFmpeg blackdetect filter and parses stderr output.
        Returns False (no black frames detected) on subprocess failure,
        treating the error conservatively so the clip is not rejected on
        probe errors alone.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(clip_path),
            "-vf",
            f"blackdetect=d={_BLACKDETECT_MIN_DURATION}:pix_th={_BLACKDETECT_PIX_TH}",
            "-f",
            "null",
            "-",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning(
                "blackdetect probe failed for %s (exit %d); skipping black-frame check",
                clip_path.name,
                proc.returncode,
            )
            return False

        stderr_text = stderr.decode(errors="replace")
        # FFmpeg emits lines like: [blackdetect @ ...] black_start:0.0 black_end:1.0 ...
        return bool(re.search(r"black_start:", stderr_text))
