"""ResourceMonitorPort — protocol for reading system resource metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import ResourceSnapshot


@runtime_checkable
class ResourceMonitorPort(Protocol):
    """Read system resource metrics (CPU, memory, temperature)."""

    async def snapshot(self) -> ResourceSnapshot: ...
