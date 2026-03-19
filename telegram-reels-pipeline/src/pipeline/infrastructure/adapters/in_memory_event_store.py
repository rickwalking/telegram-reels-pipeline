"""In-memory event store — subscribes to EventBus and stores events for DVR queries."""

from __future__ import annotations

import uuid
from collections import defaultdict

from pipeline.domain.models import PipelineEvent, StoredPipelineEvent
from pipeline.domain.types import EventId, RunId


class InMemoryPipelineEventStore:
    """In-memory implementation of PipelineEventStorePort.

    Also acts as an EventBus listener via ``__call__``.
    Events are stored per-run in insertion order.
    """

    def __init__(self) -> None:
        self._events_by_run: dict[RunId, list[StoredPipelineEvent]] = defaultdict(list)
        self._current_run_id: RunId = RunId("")

    def set_current_run_id(self, pipeline_run_id: RunId) -> None:
        """Set the active run ID for incoming events."""
        self._current_run_id = pipeline_run_id

    async def __call__(self, event: PipelineEvent) -> None:
        """EventBus listener — store the event under the current run."""
        if not self._current_run_id:
            return
        stored = _build_stored_event(event, self._current_run_id)
        self._events_by_run[self._current_run_id].append(stored)

    async def append_event(
        self,
        pipeline_run_id: RunId,
        event: PipelineEvent,
    ) -> StoredPipelineEvent:
        """Explicitly store an event under a specific run."""
        stored = _build_stored_event(event, pipeline_run_id)
        self._events_by_run[pipeline_run_id].append(stored)
        return stored

    async def list_events_for_run(
        self,
        pipeline_run_id: RunId,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[tuple[StoredPipelineEvent, ...], int]:
        """Return paginated events for a run, ascending by insertion order."""
        all_events = self._events_by_run.get(pipeline_run_id, [])
        total_count = len(all_events)
        page = all_events[offset : offset + limit]
        return tuple(page), total_count

    async def get_event_by_id(
        self,
        pipeline_run_id: RunId,
        event_id: EventId,
    ) -> StoredPipelineEvent | None:
        """Return a single event by ID, or None if not found."""
        for stored_event in self._events_by_run.get(pipeline_run_id, []):
            if stored_event.event_id == event_id:
                return stored_event
        return None


def _build_stored_event(
    event: PipelineEvent,
    pipeline_run_id: RunId,
) -> StoredPipelineEvent:
    """Create a StoredPipelineEvent with a generated UUID."""
    return StoredPipelineEvent(
        event_id=EventId(f"evt-{uuid.uuid4().hex[:12]}"),
        pipeline_run_id=pipeline_run_id,
        event=event,
    )
