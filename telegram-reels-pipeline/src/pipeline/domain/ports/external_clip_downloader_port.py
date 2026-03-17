"""ExternalClipDownloaderPort — protocol for downloading and preparing external video clips."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class ExternalClipDownloaderPort(Protocol):
    """Download and prepare external video clips for overlay."""

    async def download(self, url: str, dest_dir: Path) -> Path | None:
        """Download video from URL, strip audio, upscale to 1080x1920.

        Returns path to prepared clip, or None on failure (non-fatal).
        """
        ...
