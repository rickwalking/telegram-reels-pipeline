"""Unit tests for the get_qa_history MCP tool."""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from pipeline.domain.event_types import QA_GATE_PASSED, QA_GATE_REWORK
from pipeline.domain.events import PipelineStateEvent
from pipeline.presentation.tools.get_qa_history_tool import create_get_qa_history_tool
from tests.fakes.fake_event_store import FakeEventStore


@pytest.mark.asyncio
async def test_get_qa_history_returns_attempt_history_for_stage_with_qa_events() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    rework_event = PipelineStateEvent(
        event_id="evt-qa-001",
        pipeline_run_id="run-qa-789",
        event_type=QA_GATE_REWORK,
        stage_name="content",
        payload_data=MappingProxyType({"score": 0.6, "reason": "needs more detail"}),
        created_at="2026-03-16T10:00:00Z",
    )
    passed_event = PipelineStateEvent(
        event_id="evt-qa-002",
        pipeline_run_id="run-qa-789",
        event_type=QA_GATE_PASSED,
        stage_name="content",
        payload_data=MappingProxyType({"score": 0.9, "reason": "looks great"}),
        created_at="2026-03-16T10:05:00Z",
    )
    await fake_event_store.append_event(rework_event)
    await fake_event_store.append_event(passed_event)
    get_qa_history = create_get_qa_history_tool(fake_event_store)

    # Act
    result_json = await get_qa_history("run-qa-789", "content")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "success"
    assert result["data"]["pipeline_run_id"] == "run-qa-789"
    assert result["data"]["stage_name"] == "content"
    assert result["data"]["attempt_count"] == 2
    assert len(result["data"]["attempt_history"]) == 2
    assert result["data"]["attempt_history"][0]["event_type"] == QA_GATE_REWORK
    assert result["data"]["attempt_history"][1]["event_type"] == QA_GATE_PASSED


@pytest.mark.asyncio
async def test_get_qa_history_returns_error_when_no_qa_events_found() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    get_qa_history = create_get_qa_history_tool(fake_event_store)

    # Act
    result_json = await get_qa_history("run-qa-789", "content")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
    assert "content" in result["message"]
    assert "run-qa-789" in result["message"]


@pytest.mark.asyncio
async def test_get_qa_history_excludes_events_for_different_stage() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    event = PipelineStateEvent(
        event_id="evt-qa-003",
        pipeline_run_id="run-qa-789",
        event_type=QA_GATE_PASSED,
        stage_name="router",
        payload_data=MappingProxyType({"score": 0.95}),
        created_at="2026-03-16T09:00:00Z",
    )
    await fake_event_store.append_event(event)
    get_qa_history = create_get_qa_history_tool(fake_event_store)

    # Act — query "content" stage, only "router" QA events exist
    result_json = await get_qa_history("run-qa-789", "content")

    # Assert
    result = json.loads(result_json)
    assert result["status"] == "error"
    assert result["error_type"] == "not_found"
