"""FileDeliveryPort — protocol for uploading files to external storage."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileDeliveryPort(Protocol):
    """Upload files to external storage (Google Drive) for large file delivery."""

    async def upload(self, path: Path) -> str: ...
