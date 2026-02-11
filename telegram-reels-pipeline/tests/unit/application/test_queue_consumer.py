"""Tests for QueueConsumer — FIFO queue with file-based lifecycle."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pipeline.application.queue_consumer import QueueConsumer
from pipeline.domain.models import QueueItem

_ITEM_COUNTER = 0


def _make_item(url: str = "https://youtube.com/watch?v=test", update_id: int = 1) -> QueueItem:
    global _ITEM_COUNTER  # noqa: PLW0603
    _ITEM_COUNTER += 1
    return QueueItem(
        url=url,
        telegram_update_id=update_id,
        queued_at=datetime(2026, 2, 10, 14, 0, _ITEM_COUNTER, tzinfo=UTC),
    )


class TestQueueConsumerEnqueue:
    def test_enqueue_creates_json_file(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        item = _make_item()
        path = consumer.enqueue(item)
        assert path.exists()
        assert path.suffix == ".json"

    def test_enqueue_file_contains_item_data(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        item = _make_item()
        path = consumer.enqueue(item)
        data = json.loads(path.read_text())
        assert data["url"] == "https://youtube.com/watch?v=test"
        assert data["telegram_update_id"] == 1

    def test_enqueue_creates_directories(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())
        assert (tmp_path / "queue" / "inbox").is_dir()

    def test_enqueue_preserves_topic_focus(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=1,
            queued_at=datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC),
            topic_focus="CAP theorem",
        )
        path = consumer.enqueue(item)
        data = json.loads(path.read_text())
        assert data["topic_focus"] == "CAP theorem"


class TestQueueConsumerClaim:
    def test_claim_returns_oldest_item(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item(url="https://youtube.com/watch?v=first", update_id=1))
        consumer.enqueue(_make_item(url="https://youtube.com/watch?v=second", update_id=2))

        result = consumer.claim_next()
        assert result is not None
        item, path = result
        assert item.url == "https://youtube.com/watch?v=first"

    def test_claim_moves_to_processing(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())

        result = consumer.claim_next()
        assert result is not None
        _, path = result
        assert path.parent.name == "processing"

    def test_claim_returns_none_when_empty(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.ensure_dirs()
        assert consumer.claim_next() is None

    def test_claim_removes_from_inbox(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())
        assert consumer.pending_count() == 1

        consumer.claim_next()
        assert consumer.pending_count() == 0

    def test_claim_increments_processing(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())

        consumer.claim_next()
        assert consumer.processing_count() == 1


class TestQueueConsumerComplete:
    def test_complete_moves_to_completed(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())
        result = consumer.claim_next()
        assert result is not None
        _, proc_path = result

        completed_path = consumer.complete(proc_path)
        assert completed_path.parent.name == "completed"
        assert completed_path.exists()

    def test_complete_removes_from_processing(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item())
        result = consumer.claim_next()
        assert result is not None
        _, proc_path = result

        consumer.complete(proc_path)
        assert consumer.processing_count() == 0


class TestQueueConsumerCounts:
    def test_pending_count_empty(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        assert consumer.pending_count() == 0

    def test_pending_count_with_items(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        consumer.enqueue(_make_item(update_id=1))
        consumer.enqueue(_make_item(update_id=2))
        assert consumer.pending_count() == 2

    def test_processing_count_empty(self, tmp_path: Path) -> None:
        consumer = QueueConsumer(tmp_path / "queue")
        assert consumer.processing_count() == 0
