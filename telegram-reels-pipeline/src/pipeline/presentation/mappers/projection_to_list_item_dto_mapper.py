"""Mapper: RunStateProjection → PipelineRunListItemResponseDTO."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection
from pipeline.presentation.dtos.pipeline_run_list_item_response_dto import PipelineRunListItemResponseDTO


def map_projection_to_list_item_dto(projection: RunStateProjection) -> PipelineRunListItemResponseDTO:
    """Convert a domain projection into a compact list item response DTO."""
    return PipelineRunListItemResponseDTO(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        execution_status=projection.execution_status,
        current_stage=projection.current_stage,
        created_at=projection.created_at,
    )
