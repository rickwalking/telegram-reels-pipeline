"""Tests for the pipeline events DVR API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent
from pipeline.domain.types import RunId
from pipeline.infrastructure.adapters.in_memory_event_store import InMemoryPipelineEventStore
from pipeline.presentation.api_factory import create_api_application


@pytest.fixture
def event_store() -> InMemoryPipelineEventStore:
    """Fresh in-memory event store."""
    return InMemoryPipelineEventStore()


@pytest.fixture
def api_client(event_store: InMemoryPipelineEventStore) -> TestClient:
    """TestClient wired to the FastAPI app."""
    application = create_api_application(event_store=event_store)
    return TestClient(application)


def _make_event(event_name: str, stage: PipelineStage | None = None) -> PipelineEvent:
    """Helper to build a test PipelineEvent."""
    return PipelineEvent(
        timestamp="2026-03-18T10:00:00Z",
        event_name=event_name,
        stage=stage,
        data={"attempt": 1},
    )


PIPELINE_RUN_ID = RunId("run-2026-03-18-abc")


class TestListPipelineRunEvents:
    """GET /api/runs/{pipeline_run_id}/events tests."""

    async def test_empty_run_returns_zero_items(
        self,
        api_client: TestClient,
    ) -> None:
        # Arrange — no events seeded

        # Act
        response = api_client.get(f"/api/runs/{PIPELINE_RUN_ID}/events")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["offset"] == 0
        assert body["limit"] == 50

    async def test_returns_events_in_insertion_order(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange
        await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.stage_entered", PipelineStage.ROUTER),
        )
        await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.stage_completed", PipelineStage.ROUTER),
        )
        await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.stage_entered", PipelineStage.RESEARCH),
        )

        # Act
        response = api_client.get(f"/api/runs/{PIPELINE_RUN_ID}/events")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert body["items"][0]["event_name"] == "pipeline.stage_entered"
        assert body["items"][0]["stage"] == "router"
        assert body["items"][1]["event_name"] == "pipeline.stage_completed"
        assert body["items"][2]["stage"] == "research"

    async def test_pagination_offset_and_limit(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange — seed 5 events
        for i in range(5):
            await event_store.append_event(
                PIPELINE_RUN_ID,
                _make_event(f"event.{i}"),
            )

        # Act — request page with offset=2, limit=2
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events",
            params={"offset": 2, "limit": 2},
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 5
        assert len(body["items"]) == 2
        assert body["items"][0]["event_name"] == "event.2"
        assert body["items"][1]["event_name"] == "event.3"
        assert body["offset"] == 2
        assert body["limit"] == 2

    async def test_offset_beyond_total_returns_empty(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange
        await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.started"),
        )

        # Act
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events",
            params={"offset": 100},
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"] == []

    async def test_negative_offset_returns_422(
        self,
        api_client: TestClient,
    ) -> None:
        # Arrange — nothing

        # Act
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events",
            params={"offset": -1},
        )

        # Assert
        assert response.status_code == 422

    async def test_different_runs_are_isolated(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange
        other_run_id = RunId("run-other")
        await event_store.append_event(PIPELINE_RUN_ID, _make_event("event.a"))
        await event_store.append_event(other_run_id, _make_event("event.b"))

        # Act
        response = api_client.get(f"/api/runs/{PIPELINE_RUN_ID}/events")

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["event_name"] == "event.a"


class TestGetPipelineRunEventDetail:
    """GET /api/runs/{pipeline_run_id}/events/{event_id} tests."""

    async def test_returns_event_detail(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange
        stored = await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.stage_entered", PipelineStage.ROUTER),
        )
        target_event_id = stored.event_id

        # Act
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events/{target_event_id}",
        )

        # Assert
        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == str(target_event_id)
        assert body["pipeline_run_id"] == str(PIPELINE_RUN_ID)
        assert body["event_name"] == "pipeline.stage_entered"
        assert body["stage"] == "router"
        assert body["data"] == {"attempt": 1}

    async def test_not_found_returns_404(
        self,
        api_client: TestClient,
    ) -> None:
        # Arrange — no events seeded

        # Act
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events/evt-nonexistent",
        )

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == "Event not found"

    async def test_wrong_run_id_returns_404(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange — event exists under PIPELINE_RUN_ID
        stored = await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.started"),
        )

        # Act — query under a different run
        response = api_client.get(
            f"/api/runs/run-wrong/events/{stored.event_id}",
        )

        # Assert
        assert response.status_code == 404

    async def test_event_without_stage_returns_null_stage(
        self,
        event_store: InMemoryPipelineEventStore,
        api_client: TestClient,
    ) -> None:
        # Arrange
        stored = await event_store.append_event(
            PIPELINE_RUN_ID,
            _make_event("pipeline.started", stage=None),
        )

        # Act
        response = api_client.get(
            f"/api/runs/{PIPELINE_RUN_ID}/events/{stored.event_id}",
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["stage"] is None
