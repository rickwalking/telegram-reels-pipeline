"""Tests for DeliveryHandler — video and content delivery via Telegram."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.application.delivery_handler import (
    DeliveryHandler,
    format_descriptions,
    format_hashtags_and_music,
)
from pipeline.domain.models import ContentPackage


def _make_content(**overrides: object) -> ContentPackage:
    defaults = {
        "descriptions": ("Desc A", "Desc B"),
        "hashtags": ("#podcast", "#tech"),
        "music_suggestion": "Lo-fi beats",
        "mood_category": "chill",
    }
    defaults.update(overrides)
    return ContentPackage(**defaults)  # type: ignore[arg-type]


def _make_messaging() -> MagicMock:
    m = MagicMock()
    m.send_file = AsyncMock()
    m.notify_user = AsyncMock()
    return m


def _make_file_delivery(link: str = "https://drive.google.com/file/d/abc/view") -> MagicMock:
    fd = MagicMock()
    fd.upload = AsyncMock(return_value=link)
    return fd


class TestDeliverVideo:
    async def test_small_video_sent_via_telegram(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"x" * 1024)  # 1KB — well under 50MB

        messaging = _make_messaging()
        handler = DeliveryHandler(messaging=messaging)
        await handler._deliver_video(video)

        messaging.send_file.assert_awaited_once()
        call_args = messaging.send_file.call_args
        assert call_args.args[0] == video
        assert "Reel" in call_args.kwargs.get("caption", call_args.args[1] if len(call_args.args) > 1 else "")

    async def test_large_video_uploaded_to_drive(self, tmp_path: Path) -> None:
        video = tmp_path / "big.mp4"
        video.write_bytes(b"x" * 100)

        messaging = _make_messaging()
        file_delivery = _make_file_delivery("https://drive.google.com/file/d/xyz/view")

        handler = DeliveryHandler(messaging=messaging, file_delivery=file_delivery)

        fake_stat = MagicMock()
        fake_stat.st_size = 60 * 1024 * 1024  # 60MB

        with patch.object(type(video), "stat", return_value=fake_stat):
            await handler._deliver_video(video)

        file_delivery.upload.assert_awaited_once_with(video)
        messaging.notify_user.assert_awaited_once()
        msg = messaging.notify_user.call_args.args[0]
        assert "https://drive.google.com/file/d/xyz/view" in msg

    async def test_large_video_no_drive_falls_back_to_telegram(self, tmp_path: Path) -> None:
        video = tmp_path / "big.mp4"
        video.write_bytes(b"x" * 100)

        messaging = _make_messaging()
        handler = DeliveryHandler(messaging=messaging, file_delivery=None)

        fake_stat = MagicMock()
        fake_stat.st_size = 60 * 1024 * 1024

        with patch.object(type(video), "stat", return_value=fake_stat):
            await handler._deliver_video(video)

        messaging.send_file.assert_awaited_once()


class TestDeliverContent:
    async def test_sends_descriptions_and_metadata(self) -> None:
        messaging = _make_messaging()
        handler = DeliveryHandler(messaging=messaging)
        content = _make_content()

        await handler._deliver_content(content)

        assert messaging.notify_user.call_count == 2
        desc_msg = messaging.notify_user.call_args_list[0].args[0]
        assert "Option 1" in desc_msg
        assert "Option 2" in desc_msg


class TestDeliverFull:
    async def test_deliver_calls_video_then_content(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")
        content = _make_content()

        messaging = _make_messaging()
        handler = DeliveryHandler(messaging=messaging)
        await handler.deliver(video, content)

        # send_file for video, 2x notify_user for content
        messaging.send_file.assert_awaited_once()
        assert messaging.notify_user.call_count == 2


class TestFormatDescriptions:
    def test_single_description(self) -> None:
        content = _make_content(descriptions=("Only one",))
        result = format_descriptions(content)
        assert "Option 1:" in result
        assert "Only one" in result

    def test_multiple_descriptions_numbered(self) -> None:
        content = _make_content(descriptions=("A", "B", "C"))
        result = format_descriptions(content)
        assert "Option 1:" in result
        assert "Option 2:" in result
        assert "Option 3:" in result

    def test_descriptions_separated_by_blank_lines(self) -> None:
        content = _make_content(descriptions=("A", "B"))
        result = format_descriptions(content)
        assert "\n\n" in result


class TestFormatHashtagsAndMusic:
    def test_with_hashtags_and_mood(self) -> None:
        content = _make_content()
        result = format_hashtags_and_music(content)
        assert "#podcast" in result
        assert "#tech" in result
        assert "Lo-fi beats" in result
        assert "chill" in result

    def test_empty_hashtags(self) -> None:
        content = _make_content(hashtags=())
        result = format_hashtags_and_music(content)
        assert "(no hashtags)" in result

    def test_no_mood_category(self) -> None:
        content = _make_content(mood_category="")
        result = format_hashtags_and_music(content)
        assert "Mood:" not in result
