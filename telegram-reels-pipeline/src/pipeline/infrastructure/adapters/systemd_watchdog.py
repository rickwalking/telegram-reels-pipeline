"""SystemdWatchdog — sd_notify integration for health heartbeats."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket

logger = logging.getLogger(__name__)


def _sd_notify(state: str) -> bool:
    """Send a notification to systemd via NOTIFY_SOCKET.

    Returns True if the message was sent successfully.
    """
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return False

    if addr.startswith("@"):
        addr = "\0" + addr[1:]

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.sendto(state.encode(), addr)
        finally:
            sock.close()
    except OSError:
        logger.exception("Failed to send sd_notify: %s", state)
        return False

    return True


def notify_ready() -> bool:
    """Signal systemd that the service is ready (READY=1)."""
    return _sd_notify("READY=1")


def notify_watchdog() -> bool:
    """Send a watchdog heartbeat to systemd (WATCHDOG=1)."""
    return _sd_notify("WATCHDOG=1")


def notify_stopping() -> bool:
    """Signal systemd that the service is stopping (STOPPING=1)."""
    return _sd_notify("STOPPING=1")


def get_watchdog_usec() -> int | None:
    """Read WATCHDOG_USEC from environment.

    Returns the watchdog interval in microseconds, or None if not set.
    """
    raw = os.environ.get("WATCHDOG_USEC")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid WATCHDOG_USEC value: %s", raw)
        return None


class WatchdogHeartbeat:
    """Periodic watchdog heartbeat sender.

    Sends WATCHDOG=1 at half the systemd WatchdogSec interval.
    If WATCHDOG_USEC is not set, heartbeats are silently skipped.
    """

    def __init__(self, interval_seconds: float = 120.0) -> None:
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the periodic heartbeat loop."""
        usec = get_watchdog_usec()
        if usec is not None:
            self._interval = usec / 1_000_000 / 2
            logger.info("Watchdog interval: %.1fs (half of WatchdogSec)", self._interval)
        else:
            logger.info("No WATCHDOG_USEC — heartbeat interval: %.1fs", self._interval)

        self._task = asyncio.ensure_future(self._loop())

    async def stop(self) -> None:
        """Cancel the heartbeat loop."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _loop(self) -> None:
        """Send periodic WATCHDOG=1 heartbeats."""
        while True:
            notify_watchdog()
            await asyncio.sleep(self._interval)
