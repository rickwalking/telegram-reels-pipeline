"""MongoDB adapter for the EventStorePort — append-only event persistence."""

from __future__ import annotations

from odmantic import AIOEngine

from pipeline.domain.events import PipelineStateEvent
from pipeline.infrastructure.database.mappers.document_to_domain_event_mapper import map_document_to_domain_event
from pipeline.infrastructure.database.mappers.domain_event_to_document_mapper import map_domain_event_to_document
from pipeline.infrastructure.database.models.pipeline_event_document import PipelineEventDocument


class MongoDbEventStoreAdapter:
    """Append-only event store backed by MongoDB via ODMantic.

    Implements ``EventStorePort`` from the domain layer.
    Events are immutable once persisted — no updates or deletes.
    """

    def __init__(self, odmantic_engine: AIOEngine) -> None:
        self._odmantic_engine = odmantic_engine

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Persist a domain event as an immutable MongoDB document."""
        document = map_domain_event_to_document(event)
        await self._odmantic_engine.save(document)

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        """Retrieve all events for a pipeline run, sorted by creation time ascending."""
        documents = await self._odmantic_engine.find(
            PipelineEventDocument,
            PipelineEventDocument.pipeline_run_id == pipeline_run_id,
            sort=PipelineEventDocument.created_at,
        )
        return tuple(map_document_to_domain_event(document) for document in documents)

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        """Count events for a specific pipeline run without loading documents."""
        return await self._odmantic_engine.count(
            PipelineEventDocument,
            PipelineEventDocument.pipeline_run_id == pipeline_run_id,
        )
