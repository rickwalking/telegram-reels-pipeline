"""StateStorePort — protocol for persisting and retrieving run state projections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.events import RunStateProjection


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve pipeline run state projections."""

    async def save_state(self, projection: RunStateProjection) -> None: ...

    async def load_state(self, pipeline_run_id: str) -> RunStateProjection | None: ...

    async def list_incomplete_runs(self) -> list[RunStateProjection]: ...
