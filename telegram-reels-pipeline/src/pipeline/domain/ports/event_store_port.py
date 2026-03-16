"""EventStorePort — append-only event stream protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.events import PipelineStateEvent


@runtime_checkable
class EventStorePort(Protocol):
    """Append-only event store for pipeline state events."""

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Persist a single event to the stream."""
        ...

    async def get_events_for_run(self, pipeline_run_id: str) -> list[PipelineStateEvent]:
        """Retrieve all events for a given pipeline run, ordered by timestamp."""
        ...

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        """Return the total number of events for a given pipeline run."""
        ...
