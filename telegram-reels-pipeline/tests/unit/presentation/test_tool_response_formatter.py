"""Unit tests for MCP tool response formatters."""

from __future__ import annotations

import json

from pipeline.presentation.tools.format_error_response import format_error_response
from pipeline.presentation.tools.format_success_response import format_success_response


def test_format_success_response_includes_status_and_data() -> None:
    # Arrange
    data = {"run_id": "abc123", "stage": "transcript"}

    # Act
    result_json = format_success_response(data)

    # Assert
    parsed = json.loads(result_json)
    assert parsed["status"] == "success"
    assert parsed["data"] == data


def test_format_success_response_coerces_non_serialisable_values() -> None:
    # Arrange
    from pathlib import Path

    data: dict[str, object] = {"path": Path("/tmp/file.mp4")}

    # Act
    result_json = format_success_response(data)

    # Assert
    parsed = json.loads(result_json)
    assert parsed["status"] == "success"
    assert isinstance(parsed["data"]["path"], str)


def test_format_error_response_includes_status_error_type_and_message() -> None:
    # Arrange
    error_type = "not_found"
    message = "Pipeline run abc123 does not exist."

    # Act
    result_json = format_error_response(error_type, message)

    # Assert
    parsed = json.loads(result_json)
    assert parsed["status"] == "error"
    assert parsed["error_type"] == error_type
    assert parsed["message"] == message


def test_format_error_response_produces_valid_json() -> None:
    # Arrange
    error_type = "validation_error"
    message = "Stage name must not be empty."

    # Act
    result_json = format_error_response(error_type, message)

    # Assert — no exception raised by json.loads proves valid JSON
    parsed = json.loads(result_json)
    assert isinstance(parsed, dict)
