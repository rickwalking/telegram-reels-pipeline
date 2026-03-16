"""Mapper: PipelineEventDocument → PipelineStateEvent domain object."""

from __future__ import annotations

from types import MappingProxyType

from pipeline.domain.events import PipelineStateEvent
from pipeline.infrastructure.database.models.pipeline_event_document import PipelineEventDocument


def map_document_to_domain_event(document: PipelineEventDocument) -> PipelineStateEvent:
    """Reconstruct a domain event from a persisted MongoDB document."""
    created_at_iso = document.created_at.isoformat() if hasattr(document.created_at, "isoformat") else str(document.created_at)
    return PipelineStateEvent(
        event_id=document.event_id,
        pipeline_run_id=document.pipeline_run_id,
        event_type=document.event_type,
        stage_name=document.stage_name,
        payload_data=MappingProxyType(document.payload_data),
        created_at=created_at_iso,
    )
