"""MessagingPort — protocol for communicating with the user via Telegram."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class MessagingPort(Protocol):
    """Communicate with the user via Telegram."""

    async def ask_user(self, question: str) -> str: ...

    async def notify_user(self, message: str) -> None: ...

    async def send_file(self, path: Path, caption: str) -> None: ...
