"""RunCleaner — remove old run assets while preserving metadata."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_RETENTION_DAYS = 30

# Files to preserve during cleanup (metadata + final reel)
_KEEP_NAMES: frozenset[str] = frozenset({"run.md", "events.log"})
_KEEP_SUFFIXES: frozenset[str] = frozenset({".mp4"})


@dataclass(frozen=True)
class CleanupResult:
    """Summary of a cleanup operation."""

    runs_scanned: int
    runs_cleaned: int
    bytes_freed: int


class RunCleaner:
    """Delete old run assets while keeping run.md metadata and final Reels.

    Walks the runs directory, identifies runs older than the retention
    period, and removes intermediate artifacts (transcripts, frames,
    segment videos) while preserving run.md, events.log, and .mp4 files.
    """

    def __init__(
        self,
        runs_dir: Path,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._runs_dir = runs_dir
        self._retention = timedelta(days=retention_days)

    async def clean(self) -> CleanupResult:
        """Scan runs directory and remove old intermediate artifacts."""
        return await asyncio.to_thread(self._clean_sync)

    def _clean_sync(self) -> CleanupResult:
        """Synchronous cleanup implementation."""
        if not self._runs_dir.exists():
            return CleanupResult(runs_scanned=0, runs_cleaned=0, bytes_freed=0)

        cutoff = datetime.now(UTC) - self._retention
        scanned = 0
        cleaned = 0
        freed = 0

        for run_dir in sorted(self._runs_dir.iterdir()):
            if not run_dir.is_dir() or run_dir.is_symlink():
                continue

            scanned += 1
            run_md = run_dir / "run.md"
            if not run_md.exists():
                continue

            mtime = datetime.fromtimestamp(run_md.stat().st_mtime, tz=UTC)
            if mtime >= cutoff:
                continue

            run_freed = self._clean_run_dir(run_dir)
            if run_freed > 0:
                cleaned += 1
                freed += run_freed

        logger.info(
            "Cleanup complete: scanned=%d, cleaned=%d, freed=%.1fMB",
            scanned,
            cleaned,
            freed / (1024 * 1024),
        )
        return CleanupResult(runs_scanned=scanned, runs_cleaned=cleaned, bytes_freed=freed)

    def _clean_run_dir(self, run_dir: Path) -> int:
        """Remove non-essential files from a single run directory.

        Returns the number of bytes freed.
        """
        freed = 0
        for item in run_dir.rglob("*"):
            if not item.is_file() or item.is_symlink():
                continue
            if not item.resolve().is_relative_to(run_dir.resolve()):
                logger.warning("Skipping path outside run dir: %s", item)
                continue
            if item.name in _KEEP_NAMES:
                continue
            if item.suffix in _KEEP_SUFFIXES:
                continue

            size = item.stat().st_size
            try:
                item.unlink()
                freed += size
            except OSError:
                logger.warning("Failed to delete: %s", item)

        # Remove empty subdirectories
        for item in sorted(run_dir.rglob("*"), reverse=True):
            if item.is_dir():
                with contextlib.suppress(OSError):
                    item.rmdir()

        return freed
