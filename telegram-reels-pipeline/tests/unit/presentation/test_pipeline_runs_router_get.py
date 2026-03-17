"""Unit tests for GET /api/runs endpoints in pipeline_runs_router."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from pipeline.domain.events import RunStateProjection
from pipeline.presentation.api.pipeline_runs_router import (
    get_state_store_port,
    pipeline_runs_router,
)
from tests.fakes.fake_state_store import FakeStateStore


def _build_test_application(fake_state_store: FakeStateStore) -> FastAPI:
    """Build a minimal FastAPI app with the runs router and injected fake state store."""
    application = FastAPI()
    application.include_router(pipeline_runs_router)
    application.dependency_overrides[get_state_store_port] = lambda: fake_state_store
    return application


def _make_projection(pipeline_run_id: str, execution_status: str = "pending") -> RunStateProjection:
    """Build a minimal RunStateProjection for seeding the fake store."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        trigger_source="api_client",
        current_stage="router",
        execution_status=execution_status,
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=(),
        escalation_status="none",
        created_at="2026-03-16T12:00:00Z",
        last_updated_at="2026-03-16T12:00:00Z",
    )


@pytest.mark.asyncio
async def test_list_pipeline_runs_returns_empty_list_when_no_runs() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    application = _build_test_application(fake_state_store)

    # Act
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/runs")

    # Assert
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_pipeline_runs_returns_all_projections() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    await fake_state_store.save_state(_make_projection("run-001"))
    await fake_state_store.save_state(_make_projection("run-002"))
    application = _build_test_application(fake_state_store)

    # Act
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/runs")

    # Assert
    assert response.status_code == 200
    run_ids = {item["pipeline_run_id"] for item in response.json()}
    assert run_ids == {"run-001", "run-002"}


@pytest.mark.asyncio
async def test_list_pipeline_runs_filters_by_execution_status() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    await fake_state_store.save_state(_make_projection("run-pending-1", execution_status="pending"))
    await fake_state_store.save_state(_make_projection("run-running-1", execution_status="in_progress"))
    await fake_state_store.save_state(_make_projection("run-pending-2", execution_status="pending"))
    application = _build_test_application(fake_state_store)

    # Act
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/runs", params={"execution_status": "pending"})

    # Assert
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    for item in items:
        assert item["execution_status"] == "pending"


@pytest.mark.asyncio
async def test_get_pipeline_run_returns_200_with_correct_data() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    projection = _make_projection("run-xyz-789")
    await fake_state_store.save_state(projection)
    application = _build_test_application(fake_state_store)

    # Act
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/runs/run-xyz-789")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["pipeline_run_id"] == "run-xyz-789"
    assert body["youtube_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert body["execution_status"] == "pending"
    assert body["current_stage"] == "router"


@pytest.mark.asyncio
async def test_get_pipeline_run_returns_404_for_nonexistent_run() -> None:
    # Arrange
    fake_state_store = FakeStateStore()
    application = _build_test_application(fake_state_store)

    # Act
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        response = await client.get("/api/runs/nonexistent-run-id")

    # Assert
    assert response.status_code == 404
