"""StateStorePort — projected run-state read-model persistence interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.events import RunStateProjection


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve the projected run state read model."""

    async def save_projection(self, projection: RunStateProjection) -> None:
        """Persist (upsert) the run state projection."""
        ...

    async def load_projection(
        self, pipeline_run_id: str
    ) -> RunStateProjection | None:
        """Load the projection for a run, or None if not found."""
        ...
