"""KnowledgeBasePort — protocol for CRUD operations on the layout knowledge base."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import CropRegion


@runtime_checkable
class KnowledgeBasePort(Protocol):
    """CRUD operations on the layout knowledge base (crop-strategies.yaml)."""

    async def get_strategy(self, layout_name: str) -> CropRegion | None: ...

    async def save_strategy(self, layout_name: str, region: CropRegion) -> None: ...

    async def list_strategies(self) -> dict[str, CropRegion]: ...
