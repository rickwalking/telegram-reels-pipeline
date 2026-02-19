"""Tests for ResourceThrottler — resource gating before heavy processing."""

from __future__ import annotations

from pipeline.application.resource_throttler import ResourceThrottler, ThrottleConfig
from pipeline.domain.models import ResourceSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_1GB = 1024**3


def _snap(
    memory_used: int = 1 * _1GB,
    memory_total: int = 4 * _1GB,
    cpu: float = 50.0,
    temp: float | None = 55.0,
) -> ResourceSnapshot:
    return ResourceSnapshot(
        memory_used_bytes=memory_used,
        memory_total_bytes=memory_total,
        cpu_load_percent=cpu,
        temperature_celsius=temp,
    )


class FakeMonitor:
    """Stub ResourceMonitorPort that returns a sequence of snapshots."""

    def __init__(self, snapshots: list[ResourceSnapshot]) -> None:
        self._snapshots = list(snapshots)
        self._index = 0

    async def snapshot(self) -> ResourceSnapshot:
        snap = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        return snap


class FakeMessaging:
    """Stub MessagingPort for capturing notifications."""

    def __init__(self) -> None:
        self.notifications: list[str] = []

    async def ask_user(self, question: str) -> str:
        return ""

    async def notify_user(self, message: str) -> None:
        self.notifications.append(message)

    async def send_file(self, path: object, caption: str) -> None:
        pass


# ---------------------------------------------------------------------------
# _check_constraints tests
# ---------------------------------------------------------------------------


class TestCheckConstraints:
    def test_no_constraint_when_within_limits(self) -> None:
        monitor = FakeMonitor([_snap()])
        throttler = ResourceThrottler(monitor=monitor)

        result = throttler._check_constraints(_snap())

        assert result is None

    def test_memory_constraint(self) -> None:
        throttler = ResourceThrottler(monitor=FakeMonitor([]))

        result = throttler._check_constraints(_snap(memory_used=4 * _1GB))

        assert result is not None
        assert "Memory" in result

    def test_cpu_constraint(self) -> None:
        throttler = ResourceThrottler(monitor=FakeMonitor([]))

        result = throttler._check_constraints(_snap(cpu=95.0))

        assert result is not None
        assert "CPU" in result

    def test_temperature_constraint(self) -> None:
        throttler = ResourceThrottler(monitor=FakeMonitor([]))

        result = throttler._check_constraints(_snap(temp=85.0))

        assert result is not None
        assert "Temperature" in result

    def test_no_temperature_constraint_when_none(self) -> None:
        throttler = ResourceThrottler(monitor=FakeMonitor([]))

        result = throttler._check_constraints(_snap(temp=None))

        assert result is None

    def test_custom_config_thresholds(self) -> None:
        config = ThrottleConfig(memory_limit_bytes=2 * _1GB, cpu_limit_percent=50.0, temperature_limit_celsius=70.0)
        throttler = ResourceThrottler(monitor=FakeMonitor([]), config=config)

        assert throttler._check_constraints(_snap(memory_used=2 * _1GB + 1)) is not None
        assert throttler._check_constraints(_snap(cpu=51.0)) is not None
        assert throttler._check_constraints(_snap(temp=71.0)) is not None
        assert throttler._check_constraints(_snap(memory_used=1 * _1GB, cpu=30.0, temp=60.0)) is None


# ---------------------------------------------------------------------------
# wait_for_resources tests
# ---------------------------------------------------------------------------


class TestWaitForResources:
    async def test_returns_immediately_when_within_limits(self) -> None:
        monitor = FakeMonitor([_snap()])
        throttler = ResourceThrottler(monitor=monitor)

        await throttler.wait_for_resources()

        assert monitor._index == 1

    async def test_waits_until_resources_free(self) -> None:
        constrained = _snap(memory_used=4 * _1GB)
        ok = _snap(memory_used=1 * _1GB)
        monitor = FakeMonitor([constrained, constrained, ok])
        config = ThrottleConfig(check_interval_seconds=0.01)
        throttler = ResourceThrottler(monitor=monitor, config=config)

        await throttler.wait_for_resources()

        assert monitor._index == 3

    async def test_notifies_user_when_paused(self) -> None:
        constrained = _snap(cpu=95.0)
        ok = _snap(cpu=50.0)
        monitor = FakeMonitor([constrained, ok])
        messaging = FakeMessaging()
        config = ThrottleConfig(check_interval_seconds=0.01)
        throttler = ResourceThrottler(monitor=monitor, messaging=messaging, config=config)

        await throttler.wait_for_resources()

        assert len(messaging.notifications) == 1
        assert "paused" in messaging.notifications[0].lower()

    async def test_no_notification_without_messaging(self) -> None:
        constrained = _snap(cpu=95.0)
        ok = _snap(cpu=50.0)
        monitor = FakeMonitor([constrained, ok])
        config = ThrottleConfig(check_interval_seconds=0.01)
        throttler = ResourceThrottler(monitor=monitor, messaging=None, config=config)

        await throttler.wait_for_resources()

    async def test_notification_failure_does_not_crash(self) -> None:
        constrained = _snap(cpu=95.0)
        ok = _snap(cpu=50.0)

        class FailingMessaging(FakeMessaging):
            async def notify_user(self, message: str) -> None:
                raise ConnectionError("Telegram down")

        monitor = FakeMonitor([constrained, ok])
        config = ThrottleConfig(check_interval_seconds=0.01)
        throttler = ResourceThrottler(monitor=monitor, messaging=FailingMessaging(), config=config)

        await throttler.wait_for_resources()
