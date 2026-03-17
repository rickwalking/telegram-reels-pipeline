"""Unit tests for the get_stage_artifacts MCP tool."""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from pipeline.domain.event_types import STAGE_COMPLETED
from pipeline.domain.events import PipelineStateEvent
from pipeline.presentation.tools.get_stage_artifacts_tool import create_get_stage_artifacts_tool
from tests.fakes.fake_event_store import FakeEventStore


@pytest.mark.asyncio
async def test_get_stage_artifacts_returns_artifact_data_for_completed_stage() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    event = PipelineStateEvent(
        event_id="evt-001",
        pipeline_run_id="run-xyz-456",
        event_type=STAGE_COMPLETED,
        stage_name="research",
        payload_data=MappingProxyType({"output_file": "research-output.json", "duration_seconds": 42}),
        created_at="2026-03-16T10:00:00Z",
    )
    await fake_event_store.append_event(event)
    get_stage_artifacts = create_get_stage_artifacts_tool(fake_event_store)

    # Act
    result_json = await get_stage_artifacts("run-xyz-456", "research")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["data"]["pipeline_run_id"] == "run-xyz-456"
    assert result["data"]["stage_name"] == "research"
    assert result["data"]["artifacts"]["output_file"] == "research-output.json"
    assert result["data"]["artifacts"]["duration_seconds"] == 42


@pytest.mark.asyncio
async def test_get_stage_artifacts_returns_error_when_no_events_found() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    get_stage_artifacts = create_get_stage_artifacts_tool(fake_event_store)

    # Act
    result_json = await get_stage_artifacts("run-xyz-456", "research")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "research" in result["message"]
    assert "run-xyz-456" in result["message"]


@pytest.mark.asyncio
async def test_get_stage_artifacts_returns_error_for_different_stage_events() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    event = PipelineStateEvent(
        event_id="evt-002",
        pipeline_run_id="run-xyz-456",
        event_type=STAGE_COMPLETED,
        stage_name="router",
        payload_data=MappingProxyType({}),
        created_at="2026-03-16T09:00:00Z",
    )
    await fake_event_store.append_event(event)
    get_stage_artifacts = create_get_stage_artifacts_tool(fake_event_store)

    # Act — query a different stage than what was stored
    result_json = await get_stage_artifacts("run-xyz-456", "research")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
