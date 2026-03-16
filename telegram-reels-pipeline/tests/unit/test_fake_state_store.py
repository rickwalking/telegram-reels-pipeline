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
        loaded = await fake_store.load_state("run-001")

        # Assert
        assert loaded is not None
        assert loaded.pipeline_run_id == "run-001"
        assert loaded.youtube_url == "https://www.youtube.com/watch?v=test123"

    @pytest.mark.asyncio
    async def test_load_returns_none_for_unknown_run(self) -> None:
        # Arrange
        fake_store = FakeStateStore()

        # Act
        loaded = await fake_store.load_state("nonexistent-run")

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
        loaded = await fake_store.load_state("run-001")

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
        incomplete_runs = await fake_store.list_incomplete_runs()

        # Assert
        assert incomplete_runs == []

    @pytest.mark.asyncio
    async def test_excludes_completed_runs(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="completed"))
        await fake_store.save_state(_make_projection("run-002", execution_status="in_progress"))

        # Act
        incomplete_runs = await fake_store.list_incomplete_runs()

        # Assert
        assert len(incomplete_runs) == 1
        assert incomplete_runs[0].pipeline_run_id == "run-002"

    @pytest.mark.asyncio
    async def test_excludes_failed_runs(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="failed"))
        await fake_store.save_state(_make_projection("run-002", execution_status="pending"))

        # Act
        incomplete_runs = await fake_store.list_incomplete_runs()

        # Assert
        assert len(incomplete_runs) == 1
        assert incomplete_runs[0].pipeline_run_id == "run-002"

    @pytest.mark.asyncio
    async def test_includes_pending_and_in_progress_runs(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001", execution_status="pending"))
        await fake_store.save_state(_make_projection("run-002", execution_status="in_progress"))
        await fake_store.save_state(_make_projection("run-003", execution_status="paused"))

        # Act
        incomplete_runs = await fake_store.list_incomplete_runs()

        # Assert
        assert len(incomplete_runs) == 3

    @pytest.mark.asyncio
    async def test_returns_list_type(self) -> None:
        # Arrange
        fake_store = FakeStateStore()
        await fake_store.save_state(_make_projection("run-001"))

        # Act
        incomplete_runs = await fake_store.list_incomplete_runs()

        # Assert
        assert isinstance(incomplete_runs, list)
