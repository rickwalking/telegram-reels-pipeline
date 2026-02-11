"""Tests for TelegramBotAdapter — MessagingPort implementation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.infrastructure.telegram_bot.bot import TelegramBotAdapter, TelegramSendError


class TestTelegramBotAdapterInit:
    def test_stores_chat_id_as_int(self) -> None:
        with patch("pipeline.infrastructure.telegram_bot.bot.Bot"):
            adapter = TelegramBotAdapter(token="test-token", chat_id="12345")
        assert adapter.chat_id == 12345

    def test_creates_bot_with_token(self) -> None:
        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot:
            TelegramBotAdapter(token="test-token", chat_id="12345")
        mock_bot.assert_called_once_with(token="test-token")


class TestTelegramBotAdapterNotify:
    async def test_notify_sends_message(self) -> None:
        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        await adapter.notify_user("Hello!")
        mock_bot.send_message.assert_awaited_once_with(chat_id=42, text="Hello!")

    async def test_notify_raises_on_failure(self) -> None:
        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock(side_effect=RuntimeError("Network error"))
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        with pytest.raises(TelegramSendError, match="Failed to send notification"):
            await adapter.notify_user("Hello!")


class TestTelegramBotAdapterSendFile:
    async def test_send_file_calls_send_document(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "video.mp4"
        p.write_bytes(b"fake-video")

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_document = AsyncMock()
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        await adapter.send_file(p, caption="Test reel")
        mock_bot.send_document.assert_awaited_once()

    async def test_send_file_raises_on_failure(self, tmp_path: object) -> None:
        from pathlib import Path

        p = Path(str(tmp_path)) / "video.mp4"
        p.write_bytes(b"fake-video")

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_document = AsyncMock(side_effect=RuntimeError("Upload error"))
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        with pytest.raises(TelegramSendError, match="Failed to send file"):
            await adapter.send_file(p, caption="Test")


class TestTelegramBotAdapterAskUser:
    async def test_ask_user_returns_reply(self) -> None:
        from types import SimpleNamespace

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()

            # First get_updates (drain) returns empty, second returns a reply
            reply_update = SimpleNamespace(
                update_id=10,
                message=SimpleNamespace(chat_id=42, text="CAP theorem"),
            )
            mock_bot.get_updates = AsyncMock(side_effect=[[], [reply_update]])
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        with patch("pipeline.infrastructure.telegram_bot.bot.asyncio") as mock_asyncio:
            mock_asyncio.get_event_loop.return_value.time.side_effect = [0.0, 0.0, 0.0]
            mock_asyncio.sleep = AsyncMock()
            result = await adapter.ask_user("What topic?")

        assert result == "CAP theorem"

    async def test_ask_user_ignores_wrong_chat(self) -> None:
        from types import SimpleNamespace

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()

            wrong_chat = SimpleNamespace(
                update_id=10,
                message=SimpleNamespace(chat_id=999, text="spam"),
            )
            right_chat = SimpleNamespace(
                update_id=11,
                message=SimpleNamespace(chat_id=42, text="correct"),
            )
            mock_bot.get_updates = AsyncMock(side_effect=[[], [wrong_chat, right_chat]])
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        with patch("pipeline.infrastructure.telegram_bot.bot.asyncio") as mock_asyncio:
            mock_asyncio.get_event_loop.return_value.time.side_effect = [0.0, 0.0, 0.0]
            mock_asyncio.sleep = AsyncMock()
            result = await adapter.ask_user("Question?")

        assert result == "correct"

    async def test_ask_user_drains_stale_updates(self) -> None:
        from types import SimpleNamespace

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot") as mock_bot_cls:
            mock_bot = MagicMock()
            mock_bot.send_message = AsyncMock()

            stale = SimpleNamespace(update_id=5, message=SimpleNamespace(chat_id=42, text="old"))
            fresh = SimpleNamespace(update_id=10, message=SimpleNamespace(chat_id=42, text="new"))
            # Drain returns stale, then poll returns fresh
            mock_bot.get_updates = AsyncMock(side_effect=[[stale], [fresh]])
            mock_bot_cls.return_value = mock_bot
            adapter = TelegramBotAdapter(token="t", chat_id="42")

        with patch("pipeline.infrastructure.telegram_bot.bot.asyncio") as mock_asyncio:
            mock_asyncio.get_event_loop.return_value.time.side_effect = [0.0, 0.0, 0.0]
            mock_asyncio.sleep = AsyncMock()
            result = await adapter.ask_user("Question?")

        # Should get "new" not "old" because drain consumed "old" before watermark
        assert result == "new"


class TestTelegramBotAdapterProtocol:
    def test_satisfies_messaging_port(self) -> None:
        from pipeline.domain.ports import MessagingPort

        with patch("pipeline.infrastructure.telegram_bot.bot.Bot"):
            adapter = TelegramBotAdapter(token="t", chat_id="42")
        assert isinstance(adapter, MessagingPort)
