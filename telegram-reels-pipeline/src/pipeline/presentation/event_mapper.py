"""Mapper functions — domain StoredPipelineEvent to presentation DTOs."""

from __future__ import annotations

from pipeline.domain.models import StoredPipelineEvent
from pipeline.presentation.event_dtos import (
    PipelineEventDetailDTO,
    PipelineEventItemDTO,
)


def map_stored_event_to_item_dto(
    stored_event: StoredPipelineEvent,
) -> PipelineEventItemDTO:
    """Convert a domain StoredPipelineEvent to a list-item DTO."""
    return PipelineEventItemDTO(
        event_id=str(stored_event.event_id),
        pipeline_run_id=str(stored_event.pipeline_run_id),
        timestamp=stored_event.event.timestamp,
        event_name=stored_event.event.event_name,
        stage=stored_event.event.stage.value if stored_event.event.stage else None,
        data=dict(stored_event.event.data),
    )


def map_stored_event_to_detail_dto(
    stored_event: StoredPipelineEvent,
) -> PipelineEventDetailDTO:
    """Convert a domain StoredPipelineEvent to a detail DTO."""
    return PipelineEventDetailDTO(
        event_id=str(stored_event.event_id),
        pipeline_run_id=str(stored_event.pipeline_run_id),
        timestamp=stored_event.event.timestamp,
        event_name=stored_event.event.event_name,
        stage=stored_event.event.stage.value if stored_event.event.stage else None,
        data=dict(stored_event.event.data),
    )
