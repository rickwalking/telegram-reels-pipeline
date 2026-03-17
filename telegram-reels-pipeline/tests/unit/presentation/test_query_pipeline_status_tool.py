"""Unit tests for the query_pipeline_status MCP tool."""

from __future__ import annotations

import json

import pytest

from pipeline.domain.events import RunStateProjection
from pipeline.presentation.tools.query_pipeline_status_tool import create_query_pipeline_status_tool
from tests.fakes.fake_state_store import FakeStateStore


@pytest.mark.asyncio
async def test_query_pipeline_status_returns_success_response_for_existing_run() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    projection = RunStateProjection(
        pipeline_run_id="run-abc-123",
        youtube_url="https://youtube.com/watch?v=abc",
        current_stage="content",
        execution_status="running",
        completed_stages=("router", "research"),
        escalation_status="none",
        current_attempt_count=1,
    )
    await fake_state_store.save_state(projection)
    query_pipeline_status = create_query_pipeline_status_tool(fake_state_store)

    # Act
    result_json = await query_pipeline_status("run-abc-123")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["data"]["pipeline_run_id"] == "run-abc-123"
    assert result["data"]["current_stage"] == "content"
    assert result["data"]["execution_status"] == "running"
    assert result["data"]["completed_stages"] == ["router", "research"]
    assert result["data"]["escalation_status"] == "none"
    assert result["data"]["current_attempt_count"] == 1


@pytest.mark.asyncio
async def test_query_pipeline_status_returns_error_for_nonexistent_run() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    query_pipeline_status = create_query_pipeline_status_tool(fake_state_store)

    # Act
    result_json = await query_pipeline_status("run-does-not-exist")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "run-does-not-exist" in result["message"]
