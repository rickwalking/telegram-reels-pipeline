"""Unit tests for FakeStateStore — verifies StateStorePort contract compliance."""

from __future__ import annotations

import pytest

from pipeline.domain.events import RunStateProjection
from pipeline.domain.ports.state_store_port import StateStorePort
from tests.fakes.fake_state_store import FakeStateStore


def _make_projection(pipeline_run_id: str, execution_status: str = "pending") -> RunStateProjection:
    """Build a minimal RunStateProjection for testing."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url="https://www.youtube.com/watch?v=test123",
        trigger_source="cli",
        current_stage="router",
        execution_status=execution_status,
        created_at="2026-03-16T10:00:00Z",
        last_updated_at="2026-03-16T10:00:00Z",
    )


class TestFakeStateStoreProtocolCompliance:
    """Verify FakeStateStore satisfies the StateStorePort protocol."""

    def test_fake_state_store_implements_state_store_port(self) -> None:
        # Arrange
        fake_store = FakeStateStore()

        # Act & Assert
        assert isinstance(fake_store, StateStorePort)


class TestFakeStateStoreSaveAndLoad:
    """Verify save_state and load_state round-trip correctly."""

    @pytest.mark.asyncio
    async def test_save_and_load_round_trip(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        projection = _make_projection("run-001")

        # Act
        await fake_store.save_state(projection)
        loaded = await fake_store.load_projection("run-001")

        # Assert
        assert loaded is not None
        assert loaded.pipeline_run_id == "run-001"
        assert loaded.youtube_url == "https://www.youtube.com/watch?v=test123"

    @pytest.mark.asyncio
    async def test_load_returns_none_for_unknown_run(self) -> None:
        # Arrange
        fake_store = FakeStateStore()

        # Act
        loaded = await fake_store.load_projection("nonexistent-run")

        # Assert
        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_upserts_existing_projection(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        original_projection = _make_projection("run-001", execution_status="pending")
        updated_projection = RunStateProjection(
            pipeline_run_id="run-001",
            youtube_url="https://www.youtube.com/watch?v=test123",
            trigger_source="cli",
            current_stage="research",
            execution_status="in_progress",
            created_at="2026-03-16T10:00:00Z",
            last_updated_at="2026-03-16T10:05:00Z",
        )

        # Act
        await fake_store.save_state(original_projection)
        await fake_store.save_state(updated_projection)
        loaded = await fake_store.load_projection("run-001")

        # Assert
        assert loaded is not None
        assert loaded.current_stage == "research"
        assert loaded.execution_status == "in_progress"


class TestFakeStateStoreListIncompleteRuns:
    """Verify list_incomplete_runs filters terminal statuses."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_runs(self) -> None:
        # Arrange
        fake_store = FakeStateStore()

        # Act
        incomplete_runs = await fake_store.list_by_execution_status("pending")

        # Assert
        assert incomplete_runs == []

    @pytest.mark.asyncio
    async def test_filters_by_exact_status(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="completed"))
        await fake_store.save_state(_make_projection("run-002", execution_status="in_progress"))
        await fake_store.save_state(_make_projection("run-003", execution_status="pending"))

        # Act
        pending_runs = await fake_store.list_by_execution_status("pending")

        # Assert
        assert len(pending_runs) == 1
        assert pending_runs[0].pipeline_run_id == "run-003"

    @pytest.mark.asyncio
    async def test_returns_multiple_matching_runs(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="pending"))
        await fake_store.save_state(_make_projection("run-002", execution_status="pending"))
        await fake_store.save_state(_make_projection("run-003", execution_status="completed"))

        # Act
        pending_runs = await fake_store.list_by_execution_status("pending")

        # Assert
        assert len(pending_runs) == 2

    @pytest.mark.asyncio
    async def test_list_all_projections(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="pending"))
        await fake_store.save_state(_make_projection("run-002", execution_status="in_progress"))
        await fake_store.save_state(_make_projection("run-003", execution_status="completed"))

        # Act
        all_runs = await fake_store.list_all_projections()

        # Assert
        assert len(all_runs) == 3

    @pytest.mark.asyncio
    async def test_returns_list_type(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001"))

        # Act
        incomplete_runs = await fake_store.list_by_execution_status("pending")

        # Assert
        assert isinstance(incomplete_runs, list)
