"""QueueConsumer — FIFO queue with file-based inbox/processing/completed lifecycle."""

from __future__ import annotations

import fcntl
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from pipeline.domain.models import QueueItem

logger = logging.getLogger(__name__)


class QueueConsumer:
    """FIFO queue backed by filesystem directories.

    Layout::

        {base_dir}/
            inbox/          # Pending items (timestamp-prefixed JSON)
            processing/     # Currently being processed (moved from inbox)
            completed/      # Finished items (moved from processing)

    File locking via ``fcntl.flock`` prevents duplicate claims.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._inbox = base_dir / "inbox"
        self._processing = base_dir / "processing"
        self._completed = base_dir / "completed"

    def ensure_dirs(self) -> None:
        """Create queue directories if they don't exist."""
        for d in (self._inbox, self._processing, self._completed):
            d.mkdir(parents=True, exist_ok=True)

    def enqueue(self, item: QueueItem) -> Path:
        """Add a queue item to the inbox as a timestamp-prefixed JSON file.

        Returns the path to the created file.
        """
        self.ensure_dirs()
        ts = item.queued_at.strftime("%Y%m%d-%H%M%S-%f")
        short_id = uuid.uuid4().hex[:8]
        filename = f"{ts}-{short_id}.json"
        path = self._inbox / filename
        data = {
            "url": item.url,
            "telegram_update_id": item.telegram_update_id,
            "queued_at": item.queued_at.isoformat(),
            "topic_focus": item.topic_focus,
        }
        path.write_text(json.dumps(data, indent=2))
        logger.info("Enqueued item: %s", filename)
        return path

    def claim_next(self) -> tuple[QueueItem, Path] | None:
        """Claim the oldest inbox item by moving it to processing/.

        Uses file locking to prevent duplicate claims.
        Returns (QueueItem, processing_path) or None if inbox is empty.
        """
        self.ensure_dirs()
        candidates = sorted(self._inbox.iterdir())
        if not candidates:
            return None

        for candidate in candidates:
            if not candidate.is_file() or not candidate.name.endswith(".json"):
                continue
            try:
                return self._try_claim(candidate)
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.warning("Skipping invalid queue item %s: %s", candidate, exc)
                continue

        return None

    def _try_claim(self, inbox_path: Path) -> tuple[QueueItem, Path]:
        """Attempt to claim a single inbox file with file locking."""
        lock_path = inbox_path.with_suffix(".lock")
        with lock_path.open("w") as lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise OSError(f"Could not acquire lock on {inbox_path}") from exc

            try:
                if not inbox_path.exists():
                    raise OSError(f"Queue item {inbox_path} disappeared")

                data = json.loads(inbox_path.read_text())
                item = QueueItem(
                    url=data["url"],
                    telegram_update_id=data["telegram_update_id"],
                    queued_at=datetime.fromisoformat(data["queued_at"]),
                    topic_focus=data.get("topic_focus"),
                )

                dest = self._processing / inbox_path.name
                inbox_path.rename(dest)

                logger.info("Claimed queue item: %s", inbox_path.name)
                return item, dest
            finally:
                if lock_path.exists():
                    lock_path.unlink()

    def complete(self, processing_path: Path) -> Path:
        """Move a processing item to completed/. Returns the completed path."""
        self.ensure_dirs()
        dest = self._completed / processing_path.name
        processing_path.rename(dest)
        logger.info("Completed queue item: %s", processing_path.name)
        return dest

    def pending_count(self) -> int:
        """Count items in the inbox."""
        if not self._inbox.exists():
            return 0
        return sum(1 for p in self._inbox.iterdir() if p.is_file() and p.name.endswith(".json"))

    def processing_count(self) -> int:
        """Count items currently being processed."""
        if not self._processing.exists():
            return 0
        return sum(1 for p in self._processing.iterdir() if p.is_file() and p.name.endswith(".json"))
