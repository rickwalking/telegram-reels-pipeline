"""Port protocol for binary media file storage."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FileStoragePort(Protocol):
    """Persist and retrieve raw binary media assets scoped to a pipeline run.

    All methods are async to allow both local filesystem and remote storage
    implementations to satisfy this port without blocking the event loop.
    The filesystem layout is: <workspace_base>/runs/<pipeline_run_id>/<asset_name>.
    """

    async def save_binary_asset(self, pipeline_run_id: str, asset_name: str, binary_content: bytes) -> str:
        """Write bytes to storage atomically and return a relative asset reference.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run (no path separators).
            asset_name: File name for the asset within the run directory.
            binary_content: Raw bytes to persist.

        Returns:
            Relative asset reference string, e.g. ``runs/<pipeline_run_id>/<asset_name>``.
        """
        ...

    async def save_binary_asset_from_path(
        self, pipeline_run_id: str, asset_name: str, source_path: str
    ) -> str:
        """Copy a file from ``source_path`` into storage atomically.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run.
            asset_name: Destination file name within the run directory.
            source_path: Absolute or relative path to the source file on disk.

        Returns:
            Relative asset reference string, e.g. ``runs/<pipeline_run_id>/<asset_name>``.
        """
        ...

    async def get_asset_absolute_path(self, pipeline_run_id: str, asset_name: str) -> str:
        """Resolve the absolute filesystem path for a stored asset.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run.
            asset_name: File name of the asset within the run directory.

        Returns:
            Absolute path string pointing to the asset on disk.

        Raises:
            ValueError: If path traversal is detected in any argument.
        """
        ...

    async def list_run_assets(self, pipeline_run_id: str) -> tuple[str, ...]:
        """Return the file names of all assets stored for a given run.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run.

        Returns:
            Tuple of file name strings; empty tuple if the run directory does not exist.
        """
        ...

    async def delete_run_assets(self, pipeline_run_id: str) -> None:
        """Remove all assets and the run directory for a given run.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run.
        """
        ...
