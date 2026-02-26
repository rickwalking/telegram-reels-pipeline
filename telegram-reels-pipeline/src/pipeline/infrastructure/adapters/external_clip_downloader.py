"""ExternalClipDownloader — download external clips via yt-dlp, strip audio, upscale to 1080x1920."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

_TARGET_WIDTH = 1080
_TARGET_HEIGHT = 1920


class ExternalClipDownloader:
    """Downloads external clips via yt-dlp, strips audio, upscales to 1080x1920.

    Implements the ExternalClipDownloaderPort protocol.
    All failures are non-fatal: log a warning and return None.
    """

    async def download(self, url: str, dest_dir: Path) -> Path | None:
        """Download video from URL, strip audio, upscale to 1080x1920.

        Returns path to prepared clip, or None on failure (non-fatal).
        """
        clip_dir = dest_dir / "external_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)

        url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
        raw_path = clip_dir / f"clip-{url_hash}-raw.mp4"
        stripped_path = clip_dir / f"clip-{url_hash}-stripped.mp4"
        final_path = clip_dir / f"clip-{url_hash}.mp4"

        intermediates: list[Path] = []
        try:
            # Step 1: Download via yt-dlp
            if not await self._download_with_ytdlp(url, raw_path):
                return None
            intermediates.append(raw_path)

            # Step 2: Strip audio if present
            current = await self._strip_audio(raw_path, stripped_path)
            if current == stripped_path:
                intermediates.append(stripped_path)

            # Step 3: Upscale if not already 1080x1920
            width, height = await self._probe_resolution(current)
            if width is None or height is None:
                logger.warning("Failed to probe resolution for %s", current)
                return None

            if width != _TARGET_WIDTH or height != _TARGET_HEIGHT:
                if not await self._upscale(current, final_path):
                    return None
            else:
                # Already correct resolution — just rename/copy
                if current != final_path:
                    final_path = current

            # Step 4: Validate final file
            if not await self._validate(final_path):
                logger.warning("Validation failed for %s", final_path)
                return None

            logger.info("External clip ready: %s", final_path)
            return final_path
        except Exception as exc:
            logger.warning("External clip download failed for %s: %s", url, exc)
            return None
        finally:
            self._cleanup(intermediates, final_path)

    async def _download_with_ytdlp(self, url: str, raw_path: Path) -> bool:
        """Run yt-dlp to download the video. Returns True on success."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "-f",
                "bestvideo[ext=mp4]/best[ext=mp4]/best",
                "-o",
                str(raw_path),
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr_bytes = await proc.communicate()
            if proc.returncode != 0:
                stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
                logger.warning("yt-dlp failed (exit %d) for %s: %s", proc.returncode, url, stderr)
                return False
        except OSError as exc:
            logger.warning("yt-dlp failed to start: %s", exc)
            return False
        return raw_path.exists()

    async def _strip_audio(self, input_path: Path, output_path: Path) -> Path:
        """Strip audio track if present. Returns path to use for next step."""
        has_audio = await self._has_audio_stream(input_path)
        if not has_audio:
            return input_path

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                str(input_path),
                "-an",
                "-c:v",
                "copy",
                "-y",
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0 and output_path.exists():
                return output_path
        except OSError as exc:
            logger.warning("ffmpeg audio strip failed: %s", exc)
        return input_path

    async def _has_audio_stream(self, path: Path) -> bool:
        """Probe whether the file has an audio stream."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            if proc.returncode != 0:
                return False
            data = json.loads(stdout_bytes.decode(errors="replace"))
            streams = data.get("streams", [])
            return len(streams) > 0
        except (OSError, json.JSONDecodeError):
            return False

    async def _probe_resolution(self, path: Path) -> tuple[int | None, int | None]:
        """Probe video width and height via ffprobe."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            if proc.returncode != 0:
                return None, None
            data = json.loads(stdout_bytes.decode(errors="replace"))
            streams = data.get("streams", [])
            if not streams:
                return None, None
            return int(streams[0]["width"]), int(streams[0]["height"])
        except (OSError, json.JSONDecodeError, KeyError, ValueError, IndexError):
            return None, None

    async def _upscale(self, input_path: Path, output_path: Path) -> bool:
        """Upscale/rescale video to 1080x1920 with lanczos filter."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                str(input_path),
                "-vf",
                f"scale={_TARGET_WIDTH}:{_TARGET_HEIGHT}:flags=lanczos",
                "-c:a",
                "copy",
                "-y",
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                logger.warning("ffmpeg upscale failed (exit %d)", proc.returncode)
                return False
            return output_path.exists()
        except OSError as exc:
            logger.warning("ffmpeg upscale failed to start: %s", exc)
            return False

    async def _validate(self, path: Path) -> bool:
        """Validate the final clip: exists, has video stream, duration > 0."""
        if not path.exists():
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=duration",
                "-of",
                "json",
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            if proc.returncode != 0:
                return False
            data = json.loads(stdout_bytes.decode(errors="replace"))
            streams = data.get("streams", [])
            if not streams:
                return False
            duration = float(streams[0].get("duration", 0))
            return duration > 0
        except (OSError, json.JSONDecodeError, KeyError, ValueError, IndexError):
            return False

    @staticmethod
    def _cleanup(intermediates: list[Path], final_path: Path) -> None:
        """Remove intermediate files, keeping only the final output."""
        for path in intermediates:
            if path != final_path and path.exists():
                with contextlib.suppress(OSError):
                    path.unlink()


if TYPE_CHECKING:
    from pipeline.domain.ports import ExternalClipDownloaderPort

    _: ExternalClipDownloaderPort = ExternalClipDownloader()
