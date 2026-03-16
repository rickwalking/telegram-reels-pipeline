"""Unit tests for save_stage_output_tool — MCP tool registration and execution."""

from __future__ import annotations

import json

import pytest

from pipeline.application.use_cases.save_stage_output_use_case import SaveStageOutputUseCase
from pipeline.domain.events import RunStateProjection
from pipeline.presentation.tools.save_stage_output_tool import (
    _execute_save_stage_output,
)
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


def _make_pending_projection(pipeline_run_id: str = "run-tool-test") -> RunStateProjection:
    """Build a minimal in-progress projection for tool tests."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        trigger_source="api_client",
        current_stage="router",
        execution_status="in_progress",
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=(),
        escalation_status="none",
        created_at="2026-03-16T12:00:00+00:00",
        last_updated_at="2026-03-16T12:00:00+00:00",
    )


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    """Provide a fresh FakeEventStore."""
    return FakeEventStore()


@pytest.fixture()
def fake_state_store() -> FakeStateStore:
    """Provide a fresh FakeStateStore."""
    return FakeStateStore()


@pytest.fixture()
def save_stage_output_use_case(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> SaveStageOutputUseCase:
    """Provide a SaveStageOutputUseCase wired with fakes."""
    return SaveStageOutputUseCase(fake_event_store, fake_state_store)


async def test_valid_router_json_returns_success_response(
    save_stage_output_use_case: SaveStageOutputUseCase,
    fake_state_store: FakeStateStore,
) -> None:
    """A valid JSON payload for the router stage should return a success response."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-valid")
    await fake_state_store.save_state(projection)
    valid_payload = json.dumps(
        {
            "pipeline_run_id": "run-valid",
            "stage_name": "router",
            "generated_at": "2026-03-16T12:00:00Z",
            "tier": "short",
            "topic_focus": "AI safety",
            "elicitation_answers": {},
            "style_preference": "auto",
        }
    )

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-valid",
        "router",
        valid_payload,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert "event_id" in result["data"]
    assert result["data"]["stage_name"] == "router"


async def test_malformed_json_returns_invalid_json_error(
    save_stage_output_use_case: SaveStageOutputUseCase,
) -> None:
    """A non-parseable JSON string should return an ``invalid_json`` error response."""
    # Arrange
    broken_json = "{this is not valid JSON"

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-bad-json",
        "router",
        broken_json,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "invalid_json"


async def test_unknown_stage_name_returns_unknown_stage_error(
    save_stage_output_use_case: SaveStageOutputUseCase,
) -> None:
    """An unrecognised stage name should return an ``unknown_stage`` error response."""
    # Arrange
    valid_json_payload = json.dumps(
        {
            "pipeline_run_id": "run-x",
            "stage_name": "veo3_fire",
            "generated_at": "2026-03-16T12:00:00Z",
        }
    )

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-x",
        "veo3_fire",
        valid_json_payload,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "unknown_stage"


async def test_schema_violation_returns_validation_error(
    save_stage_output_use_case: SaveStageOutputUseCase,
) -> None:
    """A JSON payload missing required DTO fields should return a ``validation_error`` response."""
    # Arrange — router DTO requires 'tier' and 'topic_focus'
    incomplete_payload = json.dumps(
        {
            "pipeline_run_id": "run-incomplete",
            "stage_name": "router",
            "generated_at": "2026-03-16T12:00:00Z",
        }
    )

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-incomplete",
        "router",
        incomplete_payload,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


async def test_json_array_returns_validation_error(
    save_stage_output_use_case: SaveStageOutputUseCase,
) -> None:
    """A JSON array (not an object) should be rejected as a validation error."""
    # Arrange
    array_json = "[1, 2, 3]"

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-array",
        "router",
        array_json,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "validation_error"


async def test_valid_assembly_json_saves_event(
    save_stage_output_use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """A valid assembly stage payload should persist a STAGE_OUTPUT_SAVED event."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-assembly")
    await fake_state_store.save_state(projection)
    valid_assembly_payload = json.dumps(
        {
            "pipeline_run_id": "run-assembly",
            "stage_name": "assembly",
            "generated_at": "2026-03-16T12:00:00Z",
            "final_reel_path": "/workspace/final-reel.mp4",
            "total_duration_seconds": 58.5,
            "segment_count": 3,
            "quality_score": 0.92,
        }
    )

    # Act
    result_json = await _execute_save_stage_output(
        save_stage_output_use_case,
        "run-assembly",
        "assembly",
        valid_assembly_payload,
    )

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "success"
    events = await fake_event_store.get_events_for_run("run-assembly")
    assert len(events) == 1
