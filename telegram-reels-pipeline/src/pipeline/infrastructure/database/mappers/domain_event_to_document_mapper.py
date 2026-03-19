"""Mapper: PipelineStateEvent domain object → PipelineEventDocument."""

from __future__ import annotations

from datetime import datetime

from pipeline.domain.events import PipelineStateEvent
from pipeline.infrastructure.database.models.pipeline_event_document import PipelineEventDocument


def map_domain_event_to_document(event: PipelineStateEvent) -> PipelineEventDocument:
    """Convert an immutable domain event to a MongoDB document for persistence."""
    return PipelineEventDocument(
        event_id=event.event_id,
        pipeline_run_id=event.pipeline_run_id,
        event_type=event.event_type,
        stage_name=event.stage_name,
        payload_data=dict(event.payload_data),
        created_at=datetime.fromisoformat(event.created_at) if isinstance(event.created_at, str) else event.created_at,
    )
