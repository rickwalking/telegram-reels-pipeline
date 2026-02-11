"""WorkspaceManager — per-run isolated workspace factory and context manager."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Create and manage per-run workspace directories.

    Layout::

        {base_dir}/
            runs/
                <timestamp>-<short_id>/
                    run.md          # State checkpoint
                    events.log      # Event journal
                    assets/         # Stage artifacts
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._runs_dir = base_dir / "runs"

    def create_workspace(self) -> Path:
        """Create a new per-run workspace directory. Returns the workspace path."""
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        workspace = self._runs_dir / f"{ts}-{short_id}"
        workspace.mkdir()
        (workspace / "assets").mkdir()
        logger.info("Created workspace: %s", workspace.name)
        return workspace

    @asynccontextmanager
    async def managed_workspace(self) -> AsyncIterator[Path]:
        """Async context manager that creates a workspace and yields its path.

        The workspace persists after the context exits (for crash recovery).
        """
        workspace = self.create_workspace()
        try:
            yield workspace
        finally:
            logger.info("Workspace session ended: %s", workspace.name)

    def list_workspaces(self) -> list[Path]:
        """List all run workspaces sorted by name (chronological)."""
        if not self._runs_dir.exists():
            return []
        return sorted(d for d in self._runs_dir.iterdir() if d.is_dir())
