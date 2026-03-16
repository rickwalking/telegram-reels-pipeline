"""MongoDB adapter for the StateStorePort — run state projection persistence."""

from __future__ import annotations

from odmantic import AIOEngine

from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.mappers.document_to_projection_mapper import map_document_to_projection
from pipeline.infrastructure.database.mappers.projection_to_document_mapper import map_projection_to_document
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument

_TERMINAL_STATUSES: frozenset[str] = frozenset({"completed", "failed"})


class MongoDbStateStoreAdapter:
    """Run state projection store backed by MongoDB via ODMantic.

    Implements ``StateStorePort`` from the domain layer.
    Projections are upserted by ``pipeline_run_id`` on each state transition.
    """

    def __init__(self, odmantic_engine: AIOEngine) -> None:
        self._odmantic_engine = odmantic_engine

    async def save_state(self, projection: RunStateProjection) -> None:
        """Upsert a run state projection, keyed by pipeline_run_id."""
        existing_document = await self._find_document_by_run_id(projection.pipeline_run_id)
        document = map_projection_to_document(projection)
        if existing_document is not None:
            document.id = existing_document.id
        await self._odmantic_engine.save(document)

    async def load_state(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load a single run state projection by pipeline_run_id."""
        document = await self._find_document_by_run_id(pipeline_run_id)
        if document is None:
            return None
        return map_document_to_projection(document)

    async def list_incomplete_runs(self) -> list[RunStateProjection]:
        """List all run state projections not in a terminal status."""
        documents = await self._odmantic_engine.find(
            RunStateDocument,
            RunStateDocument.execution_status.not_in(_TERMINAL_STATUSES),  # type: ignore[attr-defined]
        )
        return [map_document_to_projection(document) for document in documents]

    async def _find_document_by_run_id(self, pipeline_run_id: str) -> RunStateDocument | None:
        """Find a single run state document by pipeline_run_id."""
        return await self._odmantic_engine.find_one(
            RunStateDocument,
            RunStateDocument.pipeline_run_id == pipeline_run_id,
        )
