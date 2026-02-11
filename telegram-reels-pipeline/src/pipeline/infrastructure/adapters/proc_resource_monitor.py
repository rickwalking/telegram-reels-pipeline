"""ProcResourceMonitor — read system resources from /proc and /sys on Linux."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING

from pipeline.domain.models import ResourceSnapshot

if TYPE_CHECKING:
    from pipeline.domain.ports import ResourceMonitorPort

logger = logging.getLogger(__name__)

# Raspberry Pi thermal zone path
_THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"


class ProcResourceMonitor:
    """Read CPU, memory, and temperature from Linux procfs/sysfs.

    Satisfies the ResourceMonitorPort protocol. Designed for Raspberry Pi
    but works on any Linux system with /proc/meminfo and /proc/loadavg.
    """

    if TYPE_CHECKING:
        _protocol_check: ResourceMonitorPort

    async def snapshot(self) -> ResourceSnapshot:
        """Collect a point-in-time resource snapshot."""
        memory_used, memory_total = await asyncio.to_thread(_read_memory)
        cpu_load = await asyncio.to_thread(_read_cpu_load)
        temperature = await asyncio.to_thread(_read_temperature)

        return ResourceSnapshot(
            memory_used_bytes=memory_used,
            memory_total_bytes=memory_total,
            cpu_load_percent=cpu_load,
            temperature_celsius=temperature,
        )


def _read_memory() -> tuple[int, int]:
    """Parse /proc/meminfo for total and available memory.

    Returns (used_bytes, total_bytes).
    """
    total = 0
    available = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) * 1024  # kB -> bytes
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
            if total and available:
                break

    if total == 0:
        raise OSError("Could not parse MemTotal from /proc/meminfo")
    if available == 0:
        raise OSError("Could not parse MemAvailable from /proc/meminfo")

    return total - available, total


def _read_cpu_load() -> float:
    """Read 1-minute load average and convert to percentage of online CPUs.

    Uses /proc/loadavg for the 1-minute average and os.cpu_count() for
    normalization.
    """
    with open("/proc/loadavg") as f:
        load_1m = float(f.read().split()[0])

    cpus = os.cpu_count() or 1
    return min(load_1m / cpus * 100.0, 100.0)


def _read_temperature() -> float | None:
    """Read CPU temperature from thermal_zone0 on Raspberry Pi.

    Returns degrees Celsius, or None if the thermal zone is unavailable.
    """
    try:
        with open(_THERMAL_PATH) as f:
            return int(f.read().strip()) / 1000.0
    except (FileNotFoundError, ValueError, OSError):
        return None
