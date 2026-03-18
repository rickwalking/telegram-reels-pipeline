"""Port for querying stored pipeline events — supports DVR scrubber."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.models import StoredPipelineEvent
from pipeline.domain.types import EventId, RunId


@runtime_checkable
class PipelineEventStorePort(Protocol):
    """Read-side port for querying persisted pipeline events."""

    async def list_events_for_run(
        self,
        pipeline_run_id: RunId,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[tuple[StoredPipelineEvent, ...], int]:
        """Return paginated events for a run, ordered by created_at ascending.

        Returns a tuple of (events, total_count).
        """
        ...

    async def get_event_by_id(
        self,
        pipeline_run_id: RunId,
        event_id: EventId,
    ) -> StoredPipelineEvent | None:
        """Return a single event by ID, or None if not found."""
        ...
