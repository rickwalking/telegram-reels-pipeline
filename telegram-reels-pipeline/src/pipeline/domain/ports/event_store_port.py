"""EventStorePort — protocol for appending and retrieving pipeline state events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.events import PipelineStateEvent


@runtime_checkable
class EventStorePort(Protocol):
    """Append and retrieve pipeline state events for event sourcing."""

    async def append_event(self, event: PipelineStateEvent) -> None: ...

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]: ...

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int: ...
