"""In-memory fake of EventStorePort for testing — stores events in a list."""

from __future__ import annotations

from pipeline.domain.events import PipelineStateEvent


class FakeEventStore:
    """List-backed in-memory implementation of EventStorePort.

    Append-only: events are stored in insertion order and never modified.
    """

    def __init__(self) -> None:
        self._events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Append an event to the in-memory store."""
        self._events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        """Retrieve all events for a run, preserving insertion order."""
        return tuple(event for event in self._events if event.pipeline_run_id == pipeline_run_id)

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        """Count events for a specific pipeline run."""
        return sum(1 for event in self._events if event.pipeline_run_id == pipeline_run_id)
