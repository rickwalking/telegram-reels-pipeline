"""VideoProcessingPort — protocol for FFmpeg video frame extraction and encoding."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import SegmentLayout


@runtime_checkable
class VideoProcessingPort(Protocol):
    """Process video via FFmpeg — frame extraction, crop, encode."""

    async def extract_frames(self, video: Path, timestamps: list[float]) -> list[Path]: ...

    async def crop_and_encode(self, video: Path, segments: list[SegmentLayout], output: Path) -> Path: ...
