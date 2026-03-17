"""Unit tests for presentation layer mappers."""

from __future__ import annotations

import pytest

from pipeline.domain.events import CreatePipelineRunCommand, RunStateProjection
from pipeline.presentation.dtos.create_pipeline_run_request_dto import CreatePipelineRunRequestDTO
from pipeline.presentation.dtos.pipeline_run_response_dto import PipelineRunResponseDTO
from pipeline.presentation.mappers.projection_to_response_dto_mapper import map_projection_to_response_dto
from pipeline.presentation.mappers.request_dto_to_command_mapper import map_request_dto_to_command


def test_map_request_dto_to_command_maps_youtube_url() -> None:
    # Arrange
    request_dto = CreatePipelineRunRequestDTO(
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        topic_focus="rick astley meme",
        trigger_source="api_client",
        client_identifier="user-42",
    )

    # Act
    command = map_request_dto_to_command(request_dto)

    # Assert
    assert command.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_map_request_dto_to_command_maps_topic_focus() -> None:
    # Arrange
    request_dto = CreatePipelineRunRequestDTO(
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        topic_focus="machine learning basics",
        trigger_source="api_client",
    )

    # Act
    command = map_request_dto_to_command(request_dto)

    # Assert
    assert command.topic_focus == "machine learning basics"


def test_map_request_dto_to_command_maps_trigger_source() -> None:
    # Arrange
    request_dto = CreatePipelineRunRequestDTO(
        youtube_url="https://youtu.be/dQw4w9WgXcQ",
        trigger_source="telegram_bot",
    )

    # Act
    command = map_request_dto_to_command(request_dto)

    # Assert
    assert command.trigger_source == "telegram_bot"


def test_map_request_dto_to_command_maps_client_identifier() -> None:
    # Arrange
    request_dto = CreatePipelineRunRequestDTO(
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        client_identifier="chat-99",
    )

    # Act
    command = map_request_dto_to_command(request_dto)

    # Assert
    assert command.client_identifier == "chat-99"


def test_map_request_dto_to_command_returns_create_pipeline_run_command_type() -> None:
    # Arrange
    request_dto = CreatePipelineRunRequestDTO(
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )

    # Act
    command = map_request_dto_to_command(request_dto)

    # Assert
    assert isinstance(command, CreatePipelineRunCommand)


def test_map_projection_to_response_dto_maps_pipeline_run_id() -> None:
    # Arrange
    projection = RunStateProjection(
        pipeline_run_id="run-2026-abc123",
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        trigger_source="api_client",
        current_stage="router",
        execution_status="pending",
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=(),
        escalation_status="none",
        created_at="2026-03-16T10:00:00Z",
        last_updated_at="2026-03-16T10:00:00Z",
    )

    # Act
    response_dto = map_projection_to_response_dto(projection)

    # Assert
    assert response_dto.pipeline_run_id == "run-2026-abc123"


def test_map_projection_to_response_dto_maps_all_fields() -> None:
    # Arrange
    projection = RunStateProjection(
        pipeline_run_id="run-test-full",
        youtube_url="https://www.youtube.com/watch?v=testFullMap",
        trigger_source="web_ui",
        current_stage="content",
        execution_status="in_progress",
        current_attempt_count=2,
        qa_evaluation_status="rework",
        completed_stages=("router", "research", "transcript"),
        escalation_status="none",
        created_at="2026-03-01T08:00:00Z",
        last_updated_at="2026-03-01T09:00:00Z",
    )

    # Act
    response_dto = map_projection_to_response_dto(projection)

    # Assert
    assert isinstance(response_dto, PipelineRunResponseDTO)
    assert response_dto.youtube_url == "https://www.youtube.com/watch?v=testFullMap"
    assert response_dto.trigger_source == "web_ui"
    assert response_dto.current_stage == "content"
    assert response_dto.execution_status == "in_progress"
    assert response_dto.current_attempt_count == 2
    assert response_dto.qa_evaluation_status == "rework"
    assert response_dto.completed_stages == ["router", "research", "transcript"]
    assert response_dto.escalation_status == "none"
    assert response_dto.created_at == "2026-03-01T08:00:00Z"
    assert response_dto.last_updated_at == "2026-03-01T09:00:00Z"
