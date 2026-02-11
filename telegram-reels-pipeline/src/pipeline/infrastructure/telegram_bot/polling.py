"""TelegramPoller — polls Telegram for new messages, validates, and enqueues."""

from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.domain.models import QueueItem
from pipeline.infrastructure.telegram_bot.url_validator import is_youtube_url

if TYPE_CHECKING:
    from pipeline.domain.ports import QueuePort
    from pipeline.infrastructure.telegram_bot.bot import TelegramBotAdapter

logger = logging.getLogger(__name__)

# Maximum number of update IDs to keep for deduplication
_MAX_SEEN_IDS: int = 10_000


class TelegramPoller:
    """Poll Telegram for new messages and enqueue valid YouTube URLs.

    Responsibilities:
    - Fetch new updates from Telegram via the bot adapter
    - Authenticate messages by chat_id
    - Validate YouTube URLs
    - Deduplicate by update_id (bounded LRU)
    - Enqueue valid requests via QueuePort
    """

    def __init__(
        self,
        bot: TelegramBotAdapter,
        queue: QueuePort,
        authorized_chat_id: str,
    ) -> None:
        self._bot = bot
        self._queue = queue
        self._authorized_chat_id = int(authorized_chat_id)
        self._last_update_id: int | None = None
        self._seen_update_ids: OrderedDict[int, None] = OrderedDict()

    async def poll_once(self) -> int:
        """Fetch new Telegram updates and process them.

        Returns the number of valid URLs enqueued.
        """
        try:
            updates = await self._bot.get_updates(
                offset=self._last_update_id + 1 if self._last_update_id is not None else None,
                timeout=0,
            )
        except Exception:
            logger.warning("Failed to fetch Telegram updates", exc_info=True)
            return 0

        enqueued = 0
        for update in updates:
            update_id = getattr(update, "update_id", None)
            if update_id is None:
                continue
            self._last_update_id = update_id

            # Deduplicate (bounded)
            if update_id in self._seen_update_ids:
                continue
            self._seen_update_ids[update_id] = None
            if len(self._seen_update_ids) > _MAX_SEEN_IDS:
                self._seen_update_ids.popitem(last=False)

            enqueued += await self._handle_update(update)

        return enqueued

    async def _handle_update(self, update: object) -> int:
        """Process a single Telegram update. Returns 1 if enqueued, 0 otherwise."""
        message = getattr(update, "message", None)
        if message is None:
            return 0

        chat_id = getattr(message, "chat_id", None)
        text = getattr(message, "text", None)
        update_id = getattr(update, "update_id", 0)

        # Auth check: unauthorized chat_id
        if chat_id != self._authorized_chat_id:
            logger.warning("Unauthorized message from chat_id=%s, update_id=%d", chat_id, update_id)
            return 0

        # Must have text content
        if not text:
            return 0

        text = text.strip()

        # URL validation
        if not is_youtube_url(text):
            try:
                await self._bot.notify_user("Please send a YouTube URL")
            except Exception:
                logger.warning("Failed to send rejection reply", exc_info=True)
            return 0

        # Enqueue valid YouTube URL
        item = QueueItem(
            url=text,
            telegram_update_id=update_id,
            queued_at=datetime.now(UTC),
        )
        self._queue.enqueue(item)
        logger.info("Enqueued YouTube URL: %s (update_id=%d)", text, update_id)

        try:
            pending = self._queue.pending_count()
            if pending > 1:
                await self._bot.notify_user(
                    f"Queued! You're #{pending} in line."
                )
            else:
                await self._bot.notify_user("Queued! Processing will begin shortly.")
        except Exception:
            logger.warning("Failed to send queue confirmation", exc_info=True)

        return 1

    @property
    def seen_update_ids(self) -> frozenset[int]:
        """Set of update IDs already processed (for testing/inspection)."""
        return frozenset(self._seen_update_ids)
