"""Unit tests for CreatePipelineRunRequestDTO YouTube URL validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.presentation.dtos.create_pipeline_run_request_dto import CreatePipelineRunRequestDTO


def test_valid_youtube_watch_url_is_accepted() -> None:
    # Arrange
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Act
    dto = CreatePipelineRunRequestDTO(youtube_url=valid_url)

    # Assert
    assert dto.youtube_url == valid_url


def test_valid_youtu_be_short_url_is_accepted() -> None:
    # Arrange
    valid_short_url = "https://youtu.be/dQw4w9WgXcQ"

    # Act
    dto = CreatePipelineRunRequestDTO(youtube_url=valid_short_url)

    # Assert
    assert dto.youtube_url == valid_short_url


def test_vimeo_url_is_rejected() -> None:
    # Arrange
    vimeo_url = "https://vimeo.com/12345"

    # Act / Assert
    with pytest.raises(ValidationError) as exc_info:
        CreatePipelineRunRequestDTO(youtube_url=vimeo_url)

    assert "youtube_url" in str(exc_info.value).lower() or "youtube" in str(exc_info.value).lower()


def test_empty_string_url_is_rejected() -> None:
    # Arrange
    empty_url = ""

    # Act / Assert
    with pytest.raises(ValidationError):
        CreatePipelineRunRequestDTO(youtube_url=empty_url)


def test_non_url_string_is_rejected() -> None:
    # Arrange
    not_a_url = "not-a-url"

    # Act / Assert
    with pytest.raises(ValidationError):
        CreatePipelineRunRequestDTO(youtube_url=not_a_url)


def test_default_topic_focus_is_empty_string() -> None:
    # Arrange
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Act
    dto = CreatePipelineRunRequestDTO(youtube_url=valid_url)

    # Assert
    assert dto.topic_focus == ""


def test_default_trigger_source_is_api_client() -> None:
    # Arrange
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Act
    dto = CreatePipelineRunRequestDTO(youtube_url=valid_url)

    # Assert
    assert dto.trigger_source == "api_client"


def test_default_client_identifier_is_none() -> None:
    # Arrange
    valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Act
    dto = CreatePipelineRunRequestDTO(youtube_url=valid_url)

    # Assert
    assert dto.client_identifier is None
