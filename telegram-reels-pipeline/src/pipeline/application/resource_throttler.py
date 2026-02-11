"""ResourceThrottler — defer heavy processing when Pi is under stress."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.domain.models import ResourceSnapshot
    from pipeline.domain.ports import MessagingPort, ResourceMonitorPort

logger = logging.getLogger(__name__)

# Default thresholds matching NFR-P4/P5
_DEFAULT_MEMORY_LIMIT_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB
_DEFAULT_CPU_LIMIT_PERCENT = 80.0
_DEFAULT_TEMP_LIMIT_CELSIUS = 80.0
_DEFAULT_CHECK_INTERVAL = 30.0


@dataclass(frozen=True)
class ThrottleConfig:
    """Thresholds for resource-based throttling."""

    memory_limit_bytes: int = _DEFAULT_MEMORY_LIMIT_BYTES
    cpu_limit_percent: float = _DEFAULT_CPU_LIMIT_PERCENT
    temperature_limit_celsius: float = _DEFAULT_TEMP_LIMIT_CELSIUS
    check_interval_seconds: float = _DEFAULT_CHECK_INTERVAL


class ResourceThrottler:
    """Check system resources and wait until they're within safe limits.

    Defers processing when memory, CPU, or temperature exceed thresholds.
    Notifies the user when paused and when resuming.
    """

    def __init__(
        self,
        monitor: ResourceMonitorPort,
        messaging: MessagingPort | None = None,
        config: ThrottleConfig | None = None,
    ) -> None:
        self._monitor = monitor
        self._messaging = messaging
        self._config = config or ThrottleConfig()

    async def wait_for_resources(self) -> None:
        """Block until system resources are within acceptable limits.

        Checks once; if constrained, notifies user and polls at the
        configured interval until resources free up.
        """
        snapshot = await self._monitor.snapshot()
        reason = self._check_constraints(snapshot)
        if reason is None:
            return

        logger.warning("Resource constraint detected: %s", reason)
        await self._notify_paused(reason)

        while reason is not None:
            await asyncio.sleep(self._config.check_interval_seconds)
            snapshot = await self._monitor.snapshot()
            reason = self._check_constraints(snapshot)

        logger.info("Resources available — resuming processing")

    def _check_constraints(self, snapshot: ResourceSnapshot) -> str | None:
        """Return a human-readable reason if resources are constrained, else None."""
        if snapshot.memory_used_bytes > self._config.memory_limit_bytes:
            used_gb = snapshot.memory_used_bytes / (1024**3)
            limit_gb = self._config.memory_limit_bytes / (1024**3)
            return f"Memory usage {used_gb:.1f}GB exceeds {limit_gb:.1f}GB limit"

        if snapshot.cpu_load_percent > self._config.cpu_limit_percent:
            return f"CPU load {snapshot.cpu_load_percent:.0f}% exceeds {self._config.cpu_limit_percent:.0f}% limit"

        if (
            snapshot.temperature_celsius is not None
            and snapshot.temperature_celsius > self._config.temperature_limit_celsius
        ):
            return (
                f"Temperature {snapshot.temperature_celsius:.1f}C "
                f"exceeds {self._config.temperature_limit_celsius:.1f}C limit"
            )

        return None

    async def _notify_paused(self, reason: str) -> None:
        """Send a Telegram notification that processing is paused."""
        if self._messaging is None:
            return

        msg = f"Pipeline paused \u2014 {reason}. Resuming automatically..."
        try:
            await self._messaging.notify_user(msg)
        except Exception:
            logger.exception("Failed to send throttle notification")
