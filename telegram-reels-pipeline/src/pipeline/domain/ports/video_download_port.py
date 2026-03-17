"""VideoDownloadPort — protocol for downloading video content and metadata via yt-dlp."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import VideoMetadata


@runtime_checkable
class VideoDownloadPort(Protocol):
    """Download video content and metadata via yt-dlp."""

    async def download_metadata(self, url: str) -> VideoMetadata: ...

    async def download_subtitles(self, url: str, output: Path) -> Path: ...

    async def download_video(self, url: str, output: Path) -> Path: ...
