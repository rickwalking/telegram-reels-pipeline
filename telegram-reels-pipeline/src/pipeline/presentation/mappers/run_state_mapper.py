"""Mapper between domain RunStateProjection and presentation DTOs."""

from __future__ import annotations

from pipeline.domain.events import CreatePipelineRunCommand, RunStateProjection
from pipeline.presentation.dtos.create_pipeline_run_request_dto import CreatePipelineRunRequestDTO
from pipeline.presentation.dtos.pipeline_run_response_dto import PipelineRunResponseDTO


def map_request_dto_to_command(dto: CreatePipelineRunRequestDTO) -> CreatePipelineRunCommand:
    """Convert a validated request DTO into a domain command."""
    return CreatePipelineRunCommand(
        youtube_url=dto.youtube_url,
        topic_focus=dto.topic_focus,
        trigger_source=dto.trigger_source,
    )


def map_projection_to_response_dto(projection: RunStateProjection) -> PipelineRunResponseDTO:
    """Convert a domain projection into a response DTO."""
    return PipelineRunResponseDTO(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=projection.execution_status,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=list(projection.completed_stages),
        escalation_status=projection.escalation_status,
        created_at=projection.created_at,
        last_updated_at=projection.last_updated_at,
    )
