"""FileStoragePort — binary media file persistence interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStoragePort(Protocol):
    """Store and retrieve raw binary media files (video, audio, subtitles)."""

    async def store_file(self, source_path: Path, destination_key: str) -> str:
        """Copy or move a file to storage; return the canonical storage key."""
        ...

    async def retrieve_file(self, storage_key: str, destination_path: Path) -> Path:
        """Copy a stored file to destination_path; return the written path."""
        ...
