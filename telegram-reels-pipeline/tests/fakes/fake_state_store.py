"""In-memory fake of StateStorePort for testing — stores projections in a dict."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection

_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed"})


class FakeStateStore:
    """Dict-backed in-memory implementation of StateStorePort.

    Projections are keyed by ``pipeline_run_id`` and upserted on save.
    """

    def __init__(self) -> None:
        self._projections: dict[str, RunStateProjection] = {}

    async def save_state(self, projection: RunStateProjection) -> None:
        """Upsert a run state projection by pipeline_run_id."""
        self._projections[projection.pipeline_run_id] = projection

    async def load_state(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load a run state projection by pipeline_run_id, or None."""
        return self._projections.get(pipeline_run_id)

    async def list_incomplete_runs(self) -> list[RunStateProjection]:
        """List all projections not in a terminal execution status."""
        return [
            projection
            for projection in self._projections.values()
            if projection.execution_status not in _TERMINAL_STATUSES
        ]
