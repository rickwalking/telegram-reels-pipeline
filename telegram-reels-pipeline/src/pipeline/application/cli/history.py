"""CommandHistory — debug stack of executed commands, persisted via atomic write."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path

from pipeline.domain.models import CommandRecord

logger = logging.getLogger(__name__)

_HISTORY_FILENAME = "command-history.json"


class CommandHistory:
    """Append-only stack of CommandRecord entries with atomic JSON persistence.

    Records are kept in memory and flushed to ``command-history.json``
    inside the workspace directory on each ``persist()`` call.
    """

    def __init__(self) -> None:
        self._records: list[CommandRecord] = []

    def append(self, record: CommandRecord) -> None:
        """Add a command record to the history stack."""
        self._records.append(record)

    def persist(self, workspace: Path | None) -> None:
        """Atomically write the full history to ``command-history.json``.

        If *workspace* is None or does not exist, a warning is logged and
        persistence is skipped (non-fatal).
        """
        if workspace is None:
            logger.warning("No workspace set — skipping history persist")
            return
        if not workspace.is_dir():
            logger.warning("Workspace %s does not exist — skipping history persist", workspace)
            return

        target = workspace / _HISTORY_FILENAME
        data = [
            {
                "name": r.name,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "status": r.status,
                "error": r.error,
            }
            for r in self._records
        ]

        fd, tmp_path_str = tempfile.mkstemp(dir=str(workspace), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path_str, str(target))
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path_str)
            raise

    # --- Query methods ---

    def all(self) -> tuple[CommandRecord, ...]:
        """Return all records in insertion order."""
        return tuple(self._records)

    def by_status(self, status: str) -> tuple[CommandRecord, ...]:
        """Return records matching the given status."""
        return tuple(r for r in self._records if r.status == status)

    def last(self, n: int) -> tuple[CommandRecord, ...]:
        """Return the last *n* records (or fewer if history is shorter)."""
        if n <= 0:
            return ()
        return tuple(self._records[-n:])

    def __len__(self) -> int:
        return len(self._records)
