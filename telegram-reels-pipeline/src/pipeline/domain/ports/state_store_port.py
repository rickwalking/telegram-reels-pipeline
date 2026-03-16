"""StateStorePort — protocol for persisting and retrieving pipeline run projections."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.events import RunStateProjection


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve pipeline run state projections.

    New event-sourced methods operate on RunStateProjection.
    """

    async def save_state(self, projection: RunStateProjection) -> None: ...

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None: ...

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]: ...

    async def list_all_projections(self) -> list[RunStateProjection]: ...
