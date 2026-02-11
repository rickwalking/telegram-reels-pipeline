"""Tests for SystemdWatchdog — sd_notify and heartbeat functionality."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

from pipeline.infrastructure.adapters.systemd_watchdog import (
    WatchdogHeartbeat,
    _sd_notify,
    get_watchdog_usec,
    notify_ready,
    notify_stopping,
    notify_watchdog,
)

# ---------------------------------------------------------------------------
# _sd_notify tests
# ---------------------------------------------------------------------------

class TestSdNotify:
    def test_returns_false_when_no_socket(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert _sd_notify("READY=1") is False

    def test_sends_to_unix_socket(self) -> None:
        with (
            patch.dict("os.environ", {"NOTIFY_SOCKET": "/run/test.sock"}),
            patch("socket.socket") as mock_socket,
        ):
            instance = mock_socket.return_value
            result = _sd_notify("READY=1")

            assert result is True
            instance.sendto.assert_called_once_with(b"READY=1", "/run/test.sock")
            instance.close.assert_called_once()

    def test_handles_abstract_socket(self) -> None:
        with (
            patch.dict("os.environ", {"NOTIFY_SOCKET": "@/run/test"}),
            patch("socket.socket") as mock_socket,
        ):
            instance = mock_socket.return_value
            _sd_notify("WATCHDOG=1")

            instance.sendto.assert_called_once_with(b"WATCHDOG=1", "\0/run/test")

    def test_returns_false_on_socket_error(self) -> None:
        with (
            patch.dict("os.environ", {"NOTIFY_SOCKET": "/run/test.sock"}),
            patch("socket.socket") as mock_socket,
        ):
            mock_socket.return_value.sendto.side_effect = OSError("connection refused")
            result = _sd_notify("READY=1")

            assert result is False


# ---------------------------------------------------------------------------
# Convenience function tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_notify_ready(self) -> None:
        with patch("pipeline.infrastructure.adapters.systemd_watchdog._sd_notify", return_value=True) as m:
            assert notify_ready() is True
            m.assert_called_once_with("READY=1")

    def test_notify_watchdog(self) -> None:
        with patch("pipeline.infrastructure.adapters.systemd_watchdog._sd_notify", return_value=True) as m:
            assert notify_watchdog() is True
            m.assert_called_once_with("WATCHDOG=1")

    def test_notify_stopping(self) -> None:
        with patch("pipeline.infrastructure.adapters.systemd_watchdog._sd_notify", return_value=True) as m:
            assert notify_stopping() is True
            m.assert_called_once_with("STOPPING=1")


# ---------------------------------------------------------------------------
# get_watchdog_usec tests
# ---------------------------------------------------------------------------

class TestGetWatchdogUsec:
    def test_returns_none_when_not_set(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert get_watchdog_usec() is None

    def test_returns_parsed_value(self) -> None:
        with patch.dict("os.environ", {"WATCHDOG_USEC": "300000000"}):
            assert get_watchdog_usec() == 300_000_000

    def test_returns_none_on_invalid_value(self) -> None:
        with patch.dict("os.environ", {"WATCHDOG_USEC": "not_a_number"}):
            assert get_watchdog_usec() is None


# ---------------------------------------------------------------------------
# WatchdogHeartbeat tests
# ---------------------------------------------------------------------------

class TestWatchdogHeartbeat:
    async def test_start_creates_task(self) -> None:
        heartbeat = WatchdogHeartbeat(interval_seconds=0.1)
        with patch.dict("os.environ", {}, clear=True):
            heartbeat.start()
            assert heartbeat._task is not None
            await heartbeat.stop()

    async def test_stop_cancels_task(self) -> None:
        heartbeat = WatchdogHeartbeat(interval_seconds=0.1)
        with patch.dict("os.environ", {}, clear=True):
            heartbeat.start()
            await heartbeat.stop()
            assert heartbeat._task is None

    async def test_reads_interval_from_watchdog_usec(self) -> None:
        heartbeat = WatchdogHeartbeat()
        with patch.dict("os.environ", {"WATCHDOG_USEC": "600000000"}):
            heartbeat.start()
            # 600_000_000 usec = 600s, half = 300s
            assert heartbeat._interval == 300.0
            await heartbeat.stop()

    async def test_sends_heartbeats(self) -> None:
        heartbeat = WatchdogHeartbeat(interval_seconds=0.05)
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pipeline.infrastructure.adapters.systemd_watchdog.notify_watchdog") as mock_notify,
        ):
            heartbeat.start()
            await asyncio.sleep(0.15)
            await heartbeat.stop()
            assert mock_notify.call_count >= 2

    async def test_stop_is_idempotent(self) -> None:
        heartbeat = WatchdogHeartbeat(interval_seconds=0.1)
        await heartbeat.stop()
        assert heartbeat._task is None
