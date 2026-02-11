"""Tests for TelegramPoller — polling, auth, dedup, and enqueue logic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pipeline.application.queue_consumer import QueueConsumer
from pipeline.infrastructure.telegram_bot.polling import TelegramPoller


def _make_update(update_id: int, chat_id: int, text: str) -> SimpleNamespace:
    """Create a fake Telegram update."""
    return SimpleNamespace(
        update_id=update_id,
        message=SimpleNamespace(chat_id=chat_id, text=text),
    )


def _make_poller(tmp_path: Path, chat_id: str = "42") -> tuple[TelegramPoller, MagicMock]:
    """Create a TelegramPoller with a mock bot."""
    mock_bot = MagicMock()
    mock_bot.get_updates = AsyncMock(return_value=[])
    mock_bot.notify_user = AsyncMock()
    queue = QueueConsumer(base_dir=tmp_path / "queue")
    poller = TelegramPoller(bot=mock_bot, queue=queue, authorized_chat_id=chat_id)
    return poller, mock_bot


class TestTelegramPollerValidUrl:
    async def test_enqueues_valid_youtube_url(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(1, 42, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 1
        assert poller._queue.pending_count() == 1

    async def test_sends_queue_confirmation(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(1, 42, "https://youtu.be/dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        await poller.poll_once()
        mock_bot.notify_user.assert_awaited()
        # Should contain "Queued" in one of the calls
        calls = [str(c) for c in mock_bot.notify_user.call_args_list]
        assert any("Queued" in c for c in calls)


class TestTelegramPollerInvalidUrl:
    async def test_rejects_non_youtube_url(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(1, 42, "https://www.google.com")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 0
        mock_bot.notify_user.assert_awaited_with("Please send a YouTube URL")

    async def test_rejects_plain_text(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(1, 42, "hello there")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 0


class TestTelegramPollerAuth:
    async def test_ignores_unauthorized_chat(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path, chat_id="42")
        update = _make_update(1, 999, "https://youtu.be/dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 0
        # Should NOT send any reply to unauthorized user
        mock_bot.notify_user.assert_not_awaited()

    async def test_authorized_chat_processed(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path, chat_id="42")
        update = _make_update(1, 42, "https://youtu.be/dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 1


class TestTelegramPollerDedup:
    async def test_duplicate_update_id_ignored(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(1, 42, "https://youtu.be/dQw4w9WgXcQ")

        # First poll
        mock_bot.get_updates = AsyncMock(return_value=[update])
        await poller.poll_once()

        # Second poll with same update
        mock_bot.get_updates = AsyncMock(return_value=[update])
        enqueued = await poller.poll_once()
        assert enqueued == 0

    async def test_different_update_ids_both_processed(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update1 = _make_update(1, 42, "https://youtu.be/dQw4w9WgXcQ")
        update2 = _make_update(2, 42, "https://youtu.be/abc123def45")
        mock_bot.get_updates = AsyncMock(return_value=[update1, update2])

        enqueued = await poller.poll_once()
        assert enqueued == 2

    async def test_seen_update_ids_tracked(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = _make_update(42, 42, "https://youtu.be/dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])

        await poller.poll_once()
        assert 42 in poller.seen_update_ids


class TestTelegramPollerQueuePosition:
    async def test_queue_position_when_multiple(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        # Enqueue first item directly
        from pipeline.domain.models import QueueItem

        poller._queue.enqueue(
            QueueItem(
                url="https://youtu.be/first1first",
                telegram_update_id=0,
                queued_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

        # Now poll a second URL
        update = _make_update(1, 42, "https://youtu.be/dQw4w9WgXcQ")
        mock_bot.get_updates = AsyncMock(return_value=[update])
        await poller.poll_once()

        # Should mention position in queue
        calls = [str(c) for c in mock_bot.notify_user.call_args_list]
        assert any("#2" in c for c in calls)


class TestTelegramPollerBoundedDedup:
    async def test_dedup_set_bounded(self, tmp_path: Path) -> None:
        from pipeline.infrastructure.telegram_bot.polling import _MAX_SEEN_IDS

        poller, mock_bot = _make_poller(tmp_path)
        # Use unauthorized chat_id (999) so updates are tracked in seen_update_ids
        # but never reach enqueue — avoids writing thousands of files to disk.
        updates = [
            _make_update(i, 999, "not-a-url")
            for i in range(1, _MAX_SEEN_IDS + 100)
        ]
        mock_bot.get_updates = AsyncMock(return_value=updates)
        await poller.poll_once()

        assert len(poller.seen_update_ids) <= _MAX_SEEN_IDS


class TestTelegramPollerQueuePort:
    def test_queue_consumer_satisfies_queue_port(self, tmp_path: Path) -> None:
        from pipeline.application.queue_consumer import QueueConsumer
        from pipeline.domain.ports import QueuePort

        consumer = QueueConsumer(base_dir=tmp_path / "queue")
        assert isinstance(consumer, QueuePort)


class TestTelegramPollerErrorHandling:
    async def test_handles_get_updates_failure(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        mock_bot.get_updates = AsyncMock(side_effect=RuntimeError("Network down"))

        # Should not raise
        enqueued = await poller.poll_once()
        assert enqueued == 0

    async def test_handles_no_message_in_update(self, tmp_path: Path) -> None:
        poller, mock_bot = _make_poller(tmp_path)
        update = SimpleNamespace(update_id=1, message=None)
        mock_bot.get_updates = AsyncMock(return_value=[update])

        enqueued = await poller.poll_once()
        assert enqueued == 0
