"""QueuePort — protocol for enqueueing pipeline requests and inspecting queue state."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import QueueItem


@runtime_checkable
class QueuePort(Protocol):
    """Enqueue pipeline requests and inspect queue state."""

    def enqueue(self, item: QueueItem) -> Path: ...

    def pending_count(self) -> int: ...

    def processing_count(self) -> int: ...
