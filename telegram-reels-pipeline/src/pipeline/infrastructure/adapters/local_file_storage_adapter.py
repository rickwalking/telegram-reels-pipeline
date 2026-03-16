"""Local filesystem adapter for binary media storage."""

from __future__ import annotations

import shutil
from pathlib import Path


class LocalFileStorageAdapter:
    """Implements FileStoragePort using the local filesystem with atomic writes.

    Binary media assets (video, images) are stored under:
        <workspace_base_directory>/runs/<pipeline_run_id>/<asset_name>

    All writes use a write-to-tmp-then-rename strategy to prevent partial
    reads during concurrent access. Path traversal via ``..`` is rejected
    on all public methods.
    """

    def __init__(self, workspace_base_directory: str) -> None:
        self._workspace_base = Path(workspace_base_directory)

    async def save_binary_asset(
        self, pipeline_run_id: str, asset_name: str, binary_content: bytes
    ) -> str:
        """Write bytes atomically and return the relative asset reference."""
        self._validate_path_components(pipeline_run_id, asset_name)
        run_directory = self._resolve_run_directory(pipeline_run_id)
        run_directory.mkdir(parents=True, exist_ok=True)
        final_path = run_directory / asset_name
        temporary_path = final_path.with_suffix(".tmp")
        temporary_path.write_bytes(binary_content)
        temporary_path.rename(final_path)
        return f"runs/{pipeline_run_id}/{asset_name}"

    async def save_binary_asset_from_path(
        self, pipeline_run_id: str, asset_name: str, source_path: str
    ) -> str:
        """Copy a source file atomically and return the relative asset reference."""
        self._validate_path_components(pipeline_run_id, asset_name)
        run_directory = self._resolve_run_directory(pipeline_run_id)
        run_directory.mkdir(parents=True, exist_ok=True)
        final_path = run_directory / asset_name
        temporary_path = final_path.with_suffix(".tmp")
        shutil.copy2(source_path, str(temporary_path))
        temporary_path.rename(final_path)
        return f"runs/{pipeline_run_id}/{asset_name}"

    async def get_asset_absolute_path(self, pipeline_run_id: str, asset_name: str) -> str:
        """Resolve and validate the absolute path for a stored asset."""
        self._validate_path_components(pipeline_run_id, asset_name)
        resolved_path = (self._workspace_base / "runs" / pipeline_run_id / asset_name).resolve()
        self._guard_path_traversal(resolved_path)
        return str(resolved_path)

    async def list_run_assets(self, pipeline_run_id: str) -> tuple[str, ...]:
        """Return file names of all assets in the run directory."""
        self._validate_path_components(pipeline_run_id, "")
        run_directory = self._resolve_run_directory(pipeline_run_id)
        if not run_directory.exists():
            return ()
        return tuple(entry.name for entry in run_directory.iterdir() if entry.is_file())

    async def delete_run_assets(self, pipeline_run_id: str) -> None:
        """Remove the run directory and all its assets."""
        self._validate_path_components(pipeline_run_id, "")
        run_directory = self._resolve_run_directory(pipeline_run_id)
        if run_directory.exists():
            shutil.rmtree(str(run_directory))

    def _resolve_run_directory(self, pipeline_run_id: str) -> Path:
        return self._workspace_base / "runs" / pipeline_run_id

    def _validate_path_components(self, pipeline_run_id: str, asset_name: str) -> None:
        if ".." in pipeline_run_id or "/" in pipeline_run_id or "\\" in pipeline_run_id:
            raise ValueError(f"Invalid pipeline_run_id: {pipeline_run_id!r}")
        if asset_name and (".." in asset_name or asset_name.startswith("/")):
            raise ValueError(f"Invalid asset_name: {asset_name!r}")

    def _guard_path_traversal(self, resolved_path: Path) -> None:
        workspace_resolved = self._workspace_base.resolve()
        if not str(resolved_path).startswith(str(workspace_resolved)):
            raise ValueError(f"Path traversal detected: {resolved_path}")

