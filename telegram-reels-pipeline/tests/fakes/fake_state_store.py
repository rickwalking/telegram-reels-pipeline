"""In-memory fake of StateStorePort for testing — stores projections in a dict."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection


class FakeStateStore:
    """Dict-backed in-memory implementation of StateStorePort."""

    def __init__(self) -> None:
        self._projections: dict[str, RunStateProjection] = {}

    async def save_state(self, projection: RunStateProjection) -> None:
        """Upsert a run state projection."""
        self._projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load a projection by pipeline_run_id, or None."""
        return self._projections.get(pipeline_run_id)

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
        """List projections filtered by execution status."""
        return [p for p in self._projections.values() if p.execution_status == execution_status]

    async def list_all_projections(self) -> list[RunStateProjection]:
        """List all stored projections."""
        return list(self._projections.values())
