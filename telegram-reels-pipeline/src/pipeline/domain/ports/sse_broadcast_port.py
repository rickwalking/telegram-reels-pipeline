"""SseBroadcastPort — protocol for broadcasting pipeline events via Server-Sent Events."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import PipelineEvent


@runtime_checkable
class SseBroadcastPort(Protocol):
    """Broadcast pipeline events to SSE subscribers for real-time observability."""

    async def broadcast_event(self, pipeline_run_id: str, event: PipelineEvent) -> None: ...

    def subscribe_to_run(self, pipeline_run_id: str) -> AsyncIterator[PipelineEvent]: ...
