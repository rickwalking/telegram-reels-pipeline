"""StdinReader — async stdin input with timeout implementing InputReader protocol."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.cli.protocols import InputReader

logger = logging.getLogger(__name__)


class StdinReader:
    """Read a line from stdin with a timeout.

    Satisfies the InputReader protocol. Runs ``input()`` in a background
    thread via ``asyncio.to_thread`` so the event loop stays responsive.
    Returns None on timeout, EOF, or keyboard interrupt.
    """

    if TYPE_CHECKING:
        _protocol_check: InputReader

    async def read(self, prompt: str, timeout: int) -> str | None:
        """Prompt the user and return stripped input, or None on failure."""
        try:
            raw = await asyncio.wait_for(asyncio.to_thread(input, prompt), timeout=timeout)
            return raw.strip()
        except (TimeoutError, EOFError, KeyboardInterrupt):
            return None
