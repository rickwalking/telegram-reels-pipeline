"""Delivery handler — orchestrate Reel + content delivery via Telegram."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.domain.models import ContentPackage
    from pipeline.domain.ports import FileDeliveryPort, MessagingPort

logger = logging.getLogger(__name__)

# Telegram Bot API inline file size limit
_TELEGRAM_FILE_LIMIT: int = 50 * 1024 * 1024  # 50 MB


def format_descriptions(content: ContentPackage) -> str:
    """Format description options as numbered text for Telegram delivery."""
    lines: list[str] = []
    for i, desc in enumerate(content.descriptions, start=1):
        lines.append(f"Option {i}:\n{desc}")
    return "\n\n".join(lines)


def format_hashtags_and_music(content: ContentPackage) -> str:
    """Format hashtags and music suggestion for Telegram delivery."""
    tags = " ".join(content.hashtags) if content.hashtags else "(no hashtags)"
    parts = [f"Hashtags:\n{tags}", f"Music suggestion:\n{content.music_suggestion}"]
    if content.mood_category:
        parts.append(f"Mood: {content.mood_category}")
    return "\n\n".join(parts)


class DeliveryHandler:
    """Deliver the finished Reel and content options to the user.

    Sends video via Telegram (or Google Drive for large files), followed by
    description options, hashtags, and music suggestion as structured messages.
    """

    def __init__(
        self,
        messaging: MessagingPort,
        file_delivery: FileDeliveryPort | None = None,
    ) -> None:
        self._messaging = messaging
        self._file_delivery = file_delivery

    async def deliver(self, video: Path, content: ContentPackage) -> None:
        """Deliver the complete Reel package to the user.

        Sequence: video -> descriptions -> hashtags + music.
        Large videos (>50MB) are routed to Google Drive if available.
        """
        await self._deliver_video(video)
        await self._deliver_content(content)

    async def _deliver_video(self, video: Path) -> None:
        """Send video via Telegram or Google Drive fallback."""
        stat_result = await asyncio.to_thread(video.stat)
        file_size = stat_result.st_size

        if file_size > _TELEGRAM_FILE_LIMIT and self._file_delivery is not None:
            logger.info("Video %s exceeds 50MB (%d bytes), uploading to Google Drive", video.name, file_size)
            link = await self._file_delivery.upload(video)
            await self._messaging.notify_user(f"Your Reel is ready!\nDownload: {link}")
        elif file_size > _TELEGRAM_FILE_LIMIT:
            logger.warning("Video exceeds 50MB but no file delivery adapter configured — sending via Telegram anyway")
            await self._messaging.send_file(video, caption="Your Reel (large file)")
        else:
            await self._messaging.send_file(video, caption="Here's your Reel!")

    async def _deliver_content(self, content: ContentPackage) -> None:
        """Send description options, hashtags, and music suggestion."""
        desc_text = format_descriptions(content)
        await self._messaging.notify_user(f"Description options:\n\n{desc_text}")

        meta_text = format_hashtags_and_music(content)
        await self._messaging.notify_user(meta_text)
