"""Pure mapping functions between PipelineStateEvent domain objects and PipelineEventDocument."""

from __future__ import annotations

from types import MappingProxyType

from pipeline.domain.events import PipelineStateEvent
from pipeline.infrastructure.database.models.pipeline_event_document import PipelineEventDocument


def map_domain_event_to_document(event: PipelineStateEvent) -> PipelineEventDocument:
    """Convert an immutable domain event to a MongoDB document for persistence.

    The payload MappingProxyType is serialised to a plain dict for MongoDB storage.
    """
    return PipelineEventDocument(
        event_id=event.event_id,
        pipeline_run_id=event.pipeline_run_id,
        event_type=event.event_type,
        stage_name=event.stage_name,
        payload_data=dict(event.payload),
        created_at=event.occurred_at,
    )


def map_document_to_domain_event(document: PipelineEventDocument) -> PipelineStateEvent:
    """Reconstruct a domain event from a persisted MongoDB document.

    The stored payload dict is wrapped in MappingProxyType to restore immutability.
    """
    return PipelineStateEvent(
        event_id=document.event_id,
        pipeline_run_id=document.pipeline_run_id,
        event_type=document.event_type,
        stage_name=document.stage_name,
        payload=MappingProxyType(document.payload_data),
        occurred_at=document.created_at,
    )
