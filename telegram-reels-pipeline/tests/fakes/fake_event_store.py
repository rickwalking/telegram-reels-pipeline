"""FakeEventStore — in-memory EventStorePort implementation for tests."""

from __future__ import annotations

from pipeline.domain.events import PipelineStateEvent


class FakeEventStore:
    """In-memory event store that records all appended events.

    Use ``appended_events`` to assert on emitted events in tests.
    """

    def __init__(self) -> None:
        self.appended_events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Record the event in the in-memory log."""
        self.appended_events.append(event)

    async def load_events(
        self, pipeline_run_id: str
    ) -> tuple[PipelineStateEvent, ...]:
        """Return all events matching the given run ID."""
        return tuple(
            event
            for event in self.appended_events
            if event.pipeline_run_id == pipeline_run_id
        )
