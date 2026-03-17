"""FileStoragePort — protocol for persisting raw binary media assets."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStoragePort(Protocol):
    """Persist and retrieve raw binary media assets (mp4, png) on the filesystem."""

    async def save_binary_asset(
        self, pipeline_run_id: str, asset_name: str, binary_content: bytes
    ) -> str: ...

    async def save_binary_asset_from_path(
        self, pipeline_run_id: str, asset_name: str, source_path: str
    ) -> str: ...

    async def get_asset_absolute_path(self, pipeline_run_id: str, asset_name: str) -> str: ...

    async def list_run_assets(self, pipeline_run_id: str) -> tuple[str, ...]: ...

    async def delete_run_assets(self, pipeline_run_id: str) -> None: ...
