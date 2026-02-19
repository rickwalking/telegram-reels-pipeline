"""TelegramBotAdapter — MessagingPort implementation using python-telegram-bot."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from telegram import Bot

from pipeline.domain.errors import PipelineError

if TYPE_CHECKING:
    from pipeline.domain.ports import MessagingPort

logger = logging.getLogger(__name__)

# Timeout for waiting for a user reply to ask_user
_ASK_USER_TIMEOUT_SECONDS: float = 300.0

# Polling interval when waiting for a reply
_REPLY_POLL_INTERVAL: float = 2.0


class TelegramSendError(PipelineError):
    """Failed to send a message via Telegram."""


class TelegramBotAdapter:
    """Send and receive messages via Telegram Bot API.

    Implements the MessagingPort protocol for pipeline communication.
    """

    def __init__(self, token: str, chat_id: str) -> None:
        self._bot = Bot(token=token)
        self._chat_id = int(chat_id)
        self._last_update_id: int | None = None

    @property
    def chat_id(self) -> int:
        """The authorized chat ID for this bot."""
        return self._chat_id

    async def notify_user(self, message: str) -> None:
        """Send a one-way notification message to the user."""
        try:
            await self._bot.send_message(chat_id=self._chat_id, text=message)
        except Exception as exc:
            raise TelegramSendError(f"Failed to send notification: {exc}") from exc

    async def ask_user(self, question: str) -> str:
        """Send a question and wait for the user's text reply.

        Establishes a watermark (current last_update_id) before sending the question,
        then only accepts messages with update_id > watermark. This prevents stale
        backlog messages from being mistaken for replies.

        Returns the user's reply text.
        """
        # Drain any pending updates to establish watermark
        try:
            drain = await self._bot.get_updates(
                offset=self._last_update_id + 1 if self._last_update_id is not None else None,
                timeout=0,
            )
            for update in drain:
                self._last_update_id = update.update_id
        except Exception:
            logger.warning("Failed to drain updates before ask_user", exc_info=True)

        watermark = self._last_update_id

        await self.notify_user(question)

        deadline = asyncio.get_event_loop().time() + _ASK_USER_TIMEOUT_SECONDS
        while asyncio.get_event_loop().time() < deadline:
            try:
                offset = watermark + 1 if watermark is not None else None
                updates = await self._bot.get_updates(offset=offset, timeout=0)
                for update in updates:
                    self._last_update_id = update.update_id
                    if update.message and update.message.chat_id == self._chat_id and update.message.text:
                        logger.info("Received reply to question (update_id=%d)", update.update_id)
                        return update.message.text
            except Exception:
                logger.warning("Error polling for reply, retrying", exc_info=True)

            await asyncio.sleep(_REPLY_POLL_INTERVAL)

        raise TelegramSendError(f"Timed out waiting for reply after {_ASK_USER_TIMEOUT_SECONDS}s")

    async def send_file(self, path: Path, caption: str) -> None:
        """Send a file (video/document) to the user with a caption."""
        try:
            with path.open("rb") as f:
                await self._bot.send_document(
                    chat_id=self._chat_id,
                    document=f,
                    caption=caption,
                )
        except Exception as exc:
            raise TelegramSendError(f"Failed to send file {path.name}: {exc}") from exc

    async def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[Any]:
        """Fetch raw updates from Telegram. Low-level access for TelegramPoller."""
        return list(await self._bot.get_updates(offset=offset, timeout=timeout))


if TYPE_CHECKING:
    _: MessagingPort = TelegramBotAdapter(token="", chat_id="0")
