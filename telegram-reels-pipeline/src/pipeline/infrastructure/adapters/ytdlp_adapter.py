"""YtDlpAdapter — VideoDownloadPort implementation via yt-dlp subprocess."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.domain.errors import PipelineError
from pipeline.domain.models import VideoMetadata

if TYPE_CHECKING:
    from pipeline.domain.ports import VideoDownloadPort

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES: int = 3
BASE_BACKOFF_SECONDS: float = 1.0

# Default timeout for yt-dlp operations
_DEFAULT_TIMEOUT: float = 120.0


class YtDlpError(PipelineError):
    """yt-dlp operation failed after all retries."""


class YtDlpAdapter:
    """Download video metadata, subtitles, and content via yt-dlp subprocess.

    Implements the VideoDownloadPort protocol.
    All operations use async subprocess execution with retry + exponential backoff.
    """

    def __init__(self, timeout_seconds: float = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout_seconds

    async def download_metadata(self, url: str) -> VideoMetadata:
        """Extract video metadata via yt-dlp --dump-json.

        Retries up to MAX_RETRIES times with exponential backoff.
        """
        stdout = await self._run_with_retry(
            ["yt-dlp", "--dump-json", "--no-download", url],
            operation="metadata",
        )
        return _parse_metadata(stdout, url)

    async def download_subtitles(self, url: str, output: Path) -> Path:
        """Download subtitles/auto-captions via yt-dlp.

        Tries manual subtitles first, falls back to auto-generated.
        Returns the path to the downloaded subtitle file.
        """
        output.parent.mkdir(parents=True, exist_ok=True)
        stem = output.stem

        await self._run_with_retry(
            [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang",
                "en",
                "--sub-format",
                "srt",
                "--skip-download",
                "--output",
                str(output.parent / stem),
                url,
            ],
            operation="subtitles",
        )

        # yt-dlp appends language suffix; find the actual file
        for suffix in (".en.srt", ".en.vtt", ".srt", ".vtt"):
            candidate = output.parent / f"{stem}{suffix}"
            if candidate.exists():
                return candidate

        raise YtDlpError(f"Subtitle file not found after download for {url}")

    async def download_video(self, url: str, output: Path) -> Path:
        """Download the video file via yt-dlp.

        Returns the path to the downloaded video.
        """
        output.parent.mkdir(parents=True, exist_ok=True)

        await self._run_with_retry(
            [
                "yt-dlp",
                "--format",
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--output",
                str(output),
                url,
            ],
            operation="video",
        )

        if not output.exists():
            # yt-dlp may add extension; check common patterns
            for ext in (".mp4", ".mkv", ".webm"):
                candidate = output.with_suffix(ext)
                if candidate.exists():
                    return candidate
            raise YtDlpError(f"Video file not found after download for {url}")

        return output

    async def _run_with_retry(self, cmd: list[str], operation: str) -> str:
        """Execute a yt-dlp command with exponential backoff retry.

        Returns stdout on success.
        Raises YtDlpError after all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await self._run_once(cmd)
            except (YtDlpError, OSError) as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    logger.warning(
                        "yt-dlp %s attempt %d/%d failed: %s (retrying in %.1fs)",
                        operation,
                        attempt,
                        MAX_RETRIES,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "yt-dlp %s failed after %d attempts: %s",
                        operation,
                        MAX_RETRIES,
                        exc,
                    )

        assert last_error is not None
        raise YtDlpError(f"yt-dlp {operation} failed after {MAX_RETRIES} retries") from last_error

    async def _run_once(self, cmd: list[str]) -> str:
        """Execute a single yt-dlp subprocess call."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            async with asyncio.timeout(self._timeout):
                stdout_bytes, stderr_bytes = await proc.communicate()
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise YtDlpError(f"yt-dlp timed out after {self._timeout}s") from exc
        except OSError as exc:
            raise YtDlpError(f"yt-dlp failed to start: {exc}") from exc

        returncode = proc.returncode if proc.returncode is not None else 0
        if returncode != 0:
            stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
            raise YtDlpError(f"yt-dlp exited with code {returncode}: {stderr}")

        return stdout_bytes.decode(errors="replace") if stdout_bytes else ""


def _parse_metadata(raw_json: str, url: str) -> VideoMetadata:
    """Parse yt-dlp JSON output into a VideoMetadata domain model."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise YtDlpError(f"Failed to parse yt-dlp metadata JSON: {exc}") from exc

    try:
        return VideoMetadata(
            title=data.get("title", "Unknown"),
            duration_seconds=float(data.get("duration", 0) or 0),
            channel=data.get("channel", data.get("uploader", "Unknown")),
            publish_date=data.get("upload_date", ""),
            description=data.get("description", ""),
            url=url,
        )
    except (ValueError, TypeError) as exc:
        raise YtDlpError(f"Invalid metadata values: {exc}") from exc


if TYPE_CHECKING:
    _: VideoDownloadPort = YtDlpAdapter()
