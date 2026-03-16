"""Tests for RecoverPipelineRunUseCase — finding and replaying incomplete runs."""

from __future__ import annotations

from pipeline.application.use_cases.recover_pipeline_run_use_case import (
    RecoverPipelineRunUseCase,
)
from pipeline.domain.event_types import STAGE_COMPLETED, STAGE_ENTERED
from pipeline.domain.events import PipelineStateEvent, RunStateProjection
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


def _make_use_case() -> tuple[RecoverPipelineRunUseCase, FakeEventStore, FakeStateStore]:
    """Create use case with fresh fakes."""
    event_store = FakeEventStore()
    state_store = FakeStateStore()
    use_case = RecoverPipelineRunUseCase(event_store=event_store, state_store=state_store)
    return use_case, event_store, state_store


def _make_event(pipeline_run_id: str, event_type: str, stage_name: str, event_id: str) -> PipelineStateEvent:
    """Build a test event."""
    return PipelineStateEvent(
        event_id=event_id,
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        created_at="2026-03-16T10:00:00Z",
        stage_name=stage_name,
    )


class TestRecoveryWithNoIncompleteRuns:
    """Recovery when no incomplete runs exist."""

    async def test_returns_empty_list(self) -> None:
        # Arrange
        use_case, _event_store, _state_store = _make_use_case()

        # Act
        result = await use_case.execute()

        # Assert
        assert result == []


class TestRecoveryFindsLastCompletedStage:
    """Recovery replays events to determine resume point."""

    async def test_recovers_single_run_with_completed_stages(self) -> None:
        # Arrange
        use_case, event_store, state_store = _make_use_case()
        pipeline_run_id = "run-recovery-001"

        # Seed a running projection
        projection = RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://youtube.com/watch?v=test",
            current_stage="transcript",
            execution_status="running",
        )
        await state_store.save_state(projection)

        # Seed events showing router and research completed
        await event_store.append_event(_make_event(pipeline_run_id, STAGE_ENTERED, "router", "evt-1"))
        await event_store.append_event(_make_event(pipeline_run_id, STAGE_COMPLETED, "router", "evt-2"))
        await event_store.append_event(_make_event(pipeline_run_id, STAGE_ENTERED, "research", "evt-3"))
        await event_store.append_event(_make_event(pipeline_run_id, STAGE_COMPLETED, "research", "evt-4"))

        # Act
        result = await use_case.execute()

        # Assert
        assert len(result) == 1
        recovered = result[0]
        assert recovered.pipeline_run_id == pipeline_run_id
        assert recovered.execution_status == "recovering"
        assert "router" in recovered.completed_stages
        assert "research" in recovered.completed_stages
        assert recovered.current_stage == "research"

    async def test_recovers_run_with_no_completed_events(self) -> None:
        # Arrange
        use_case, event_store, state_store = _make_use_case()
        pipeline_run_id = "run-recovery-002"

        projection = RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://youtube.com/watch?v=test",
            current_stage="router",
            execution_status="running",
        )
        await state_store.save_state(projection)

        # Only an entered event, no completions
        await event_store.append_event(_make_event(pipeline_run_id, STAGE_ENTERED, "router", "evt-1"))

        # Act
        result = await use_case.execute()

        # Assert
        assert len(result) == 1
        recovered = result[0]
        assert recovered.completed_stages == ()
        assert recovered.current_stage == "router"

    async def test_persists_recovered_projection(self) -> None:
        # Arrange
        use_case, event_store, state_store = _make_use_case()
        pipeline_run_id = "run-recovery-003"

        projection = RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://youtube.com/watch?v=test",
            current_stage="content",
            execution_status="running",
        )
        await state_store.save_state(projection)

        await event_store.append_event(_make_event(pipeline_run_id, STAGE_COMPLETED, "router", "evt-1"))

        # Act
        await use_case.execute()

        # Assert
        saved = await state_store.load_projection(pipeline_run_id)
        assert saved is not None
        assert saved.execution_status == "recovering"

    async def test_skips_non_running_projections(self) -> None:
        # Arrange
        use_case, event_store, state_store = _make_use_case()

        # A completed projection should not be recovered
        completed = RunStateProjection(
            pipeline_run_id="run-done",
            youtube_url="https://youtube.com/watch?v=test",
            current_stage="delivery",
            execution_status="completed",
        )
        await state_store.save_state(completed)

        # A failed projection should not be recovered
        failed = RunStateProjection(
            pipeline_run_id="run-failed",
            youtube_url="https://youtube.com/watch?v=test",
            current_stage="research",
            execution_status="failed",
        )
        await state_store.save_state(failed)

        # Act
        result = await use_case.execute()

        # Assert
        assert result == []
