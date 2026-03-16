"""FakeEventStore — in-memory EventStorePort for testing."""

from __future__ import annotations

from pipeline.domain.events import PipelineStateEvent


class FakeEventStore:
    """In-memory append-only event store for testing."""

    def __init__(self) -> None:
        self.events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Append event to in-memory list."""
        self.events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> list[PipelineStateEvent]:
        """Filter events by pipeline run ID."""
        return [e for e in self.events if e.pipeline_run_id == pipeline_run_id]

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        """Count events for a pipeline run."""
        return len(await self.get_events_for_run(pipeline_run_id))
