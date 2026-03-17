"""Mapper: CreatePipelineRunRequestDTO → CreatePipelineRunCommand."""

from __future__ import annotations

from pipeline.domain.events import CreatePipelineRunCommand
from pipeline.presentation.dtos.create_pipeline_run_request_dto import CreatePipelineRunRequestDTO


def map_request_dto_to_command(dto: CreatePipelineRunRequestDTO) -> CreatePipelineRunCommand:
    """Convert a validated request DTO into a domain command."""
    return CreatePipelineRunCommand(
        youtube_url=dto.youtube_url,
        topic_focus=dto.topic_focus,
        trigger_source=dto.trigger_source,
        client_identifier=dto.client_identifier or "",
    )
