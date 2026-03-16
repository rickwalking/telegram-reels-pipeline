"""FakeStateStore — in-memory projection store for testing."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection


class FakeStateStore:
    """In-memory projection store for testing."""

    def __init__(self) -> None:
        self.projections: dict[str, RunStateProjection] = {}

    async def save_projection(self, projection: RunStateProjection) -> None:
        """Save projection to in-memory dict."""
        self.projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load projection by ID from in-memory dict."""
        return self.projections.get(pipeline_run_id)

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
        """Filter projections by execution status."""
        return [p for p in self.projections.values() if p.execution_status == execution_status]

    async def list_all_projections(self) -> list[RunStateProjection]:
        """Return all stored projections."""
        return list(self.projections.values())
