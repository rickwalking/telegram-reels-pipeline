"""StateStorePort — projection persistence protocol for event-sourced state."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pipeline.domain.events import RunStateProjection


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve materialized RunStateProjection views."""

    async def save_projection(self, projection: RunStateProjection) -> None:
        """Persist a materialized projection."""
        ...

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load a projection by pipeline run ID. Returns None if not found."""
        ...

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
        """List all projections matching the given execution status."""
        ...

    async def list_all_projections(self) -> list[RunStateProjection]:
        """List all stored projections."""
        ...
