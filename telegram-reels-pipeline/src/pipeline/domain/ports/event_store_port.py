"""EventStorePort — append-only event persistence interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.events import PipelineStateEvent


@runtime_checkable
class EventStorePort(Protocol):
    """Persist and retrieve pipeline state events (append-only log)."""

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Append a new event to the store for the given run."""
        ...

    async def load_events(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        """Load all events for a pipeline run in insertion order."""
        ...
