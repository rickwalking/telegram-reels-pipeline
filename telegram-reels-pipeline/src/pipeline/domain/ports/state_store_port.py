"""StateStorePort — protocol for persisting and retrieving pipeline run state."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import RunState
    from pipeline.domain.types import RunId


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve pipeline run state."""

    async def save_state(self, state: RunState) -> None: ...

    async def load_state(self, run_id: RunId) -> RunState | None: ...

    async def list_incomplete_runs(self) -> list[RunState]: ...
