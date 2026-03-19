"""In-memory fake of StateStorePort for testing — stores projections in a dict."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection


class FakeStateStore:
    """Dict-backed in-memory implementation of StateStorePort."""

    def __init__(self) -> None:
        self._projections: dict[str, RunStateProjection] = {}

    @property
    def projections(self) -> dict[str, RunStateProjection]:
        """Public access for test assertions."""
        return self._projections

    async def save_state(self, projection: RunStateProjection) -> None:
        """Upsert a run state projection."""
        self._projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load a projection by pipeline_run_id, or None."""
        return self._projections.get(pipeline_run_id)

    async def list_by_execution_status(self, execution_status: str) -> tuple[RunStateProjection, ...]:
        """List projections filtered by execution status."""
        return tuple(p for p in self._projections.values() if p.execution_status == execution_status)

    async def list_all_projections(self) -> tuple[RunStateProjection, ...]:
        """List all stored projections."""
        return tuple(self._projections.values())
