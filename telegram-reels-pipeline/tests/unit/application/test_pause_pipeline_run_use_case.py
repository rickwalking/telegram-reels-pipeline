"""Unit tests for PausePipelineRunUseCase."""

from __future__ import annotations

import pytest

from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService
from pipeline.application.use_cases.pause_pipeline_run_use_case import PauseCommand, PausePipelineRunUseCase
from pipeline.application.use_cases.run_state_projection import (
    EXECUTION_STATUS_COMPLETED,
    EXECUTION_STATUS_FAILED,
    EXECUTION_STATUS_IN_PROGRESS,
)
from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.errors import ValidationError
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_state_store import FakeStateStore


def _make_run_state(
    pipeline_run_id: str = "run-2026-01-01-abc",
    stage: PipelineStage = PipelineStage.RESEARCH,
    qa_status: QAStatus = QAStatus.PENDING,
) -> RunState:
    """Factory for a RunState with sensible defaults."""
    return RunState(
        run_id=RunId(pipeline_run_id),
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        current_stage=stage,
        current_attempt=1,
        qa_status=qa_status,
        stages_completed=("router",),
        escalation_state=EscalationState.NONE,
        created_at="2026-01-01T10:00:00Z",
        updated_at="2026-01-01T10:05:00Z",
    )


def _make_use_case(
    state_store: FakeStateStore | None = None,
    event_bus: FakeEventBus | None = None,
) -> tuple[PausePipelineRunUseCase, FakeStateStore, FakeEventBus]:
    """Build a PausePipelineRunUseCase with fake collaborators."""
    fake_store = state_store or FakeStateStore()
    fake_bus = event_bus or FakeEventBus()
    service = PipelineEventEmitterService(event_bus=fake_bus)  # type: ignore[arg-type]
    use_case = PausePipelineRunUseCase(state_store=fake_store, event_emitter=service)  # type: ignore[arg-type]
    return use_case, fake_store, fake_bus


class TestPauseActiveRun:
    async def test_pause_active_run_emits_paused_event(self) -> None:
        # Arrange
        run_id = "run-active-001"
        use_case, fake_store, fake_bus = _make_use_case()
        await fake_store.save_state(_make_run_state(pipeline_run_id=run_id))
        command = PauseCommand(pipeline_run_id=run_id, reason="user requested pause")

        # Act
        projection = await use_case.execute(command)

        # Assert
        assert projection.execution_status == EXECUTION_STATUS_IN_PROGRESS
        paused_events = fake_bus.events_by_name("pipeline.run_paused")
        assert len(paused_events) == 1
        assert paused_events[0].data["pipeline_run_id"] == run_id
        assert paused_events[0].data["reason"] == "user requested pause"

    async def test_pause_active_run_returns_projection_with_correct_run_id(self) -> None:
        # Arrange
        run_id = "run-active-002"
        use_case, fake_store, _ = _make_use_case()
        await fake_store.save_state(_make_run_state(pipeline_run_id=run_id))
        command = PauseCommand(pipeline_run_id=run_id)

        # Act
        projection = await use_case.execute(command)

        # Assert
        assert projection.pipeline_run_id == RunId(run_id)
        assert projection.current_stage == PipelineStage.RESEARCH.value

    async def test_pause_active_run_emits_reason_in_event(self) -> None:
        # Arrange
        run_id = "run-active-003"
        use_case, fake_store, fake_bus = _make_use_case()
        await fake_store.save_state(_make_run_state(pipeline_run_id=run_id))
        command = PauseCommand(pipeline_run_id=run_id, reason="maintenance window")

        # Act
        await use_case.execute(command)

        # Assert
        paused_events = fake_bus.events_by_name("pipeline.run_paused")
        assert paused_events[0].data["reason"] == "maintenance window"

    async def test_pause_active_run_with_empty_reason_emits_event(self) -> None:
        # Arrange
        run_id = "run-active-004"
        use_case, fake_store, fake_bus = _make_use_case()
        await fake_store.save_state(_make_run_state(pipeline_run_id=run_id))
        command = PauseCommand(pipeline_run_id=run_id)

        # Act
        await use_case.execute(command)

        # Assert
        paused_events = fake_bus.events_by_name("pipeline.run_paused")
        assert len(paused_events) == 1
        assert paused_events[0].data["reason"] == ""


class TestPauseNonPausableRun:
    async def test_pause_completed_run_raises_validation_error(self) -> None:
        # Arrange
        run_id = "run-completed-001"
        use_case, fake_store, _ = _make_use_case()
        completed_state = _make_run_state(
            pipeline_run_id=run_id,
            stage=PipelineStage.COMPLETED,
            qa_status=QAStatus.PASSED,
        )
        await fake_store.save_state(completed_state)
        command = PauseCommand(pipeline_run_id=run_id)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(command)

        assert EXECUTION_STATUS_COMPLETED in exc_info.value.message

    async def test_pause_failed_run_raises_validation_error(self) -> None:
        # Arrange
        run_id = "run-failed-001"
        use_case, fake_store, _ = _make_use_case()
        failed_state = _make_run_state(
            pipeline_run_id=run_id,
            stage=PipelineStage.FAILED,
            qa_status=QAStatus.FAILED,
        )
        await fake_store.save_state(failed_state)
        command = PauseCommand(pipeline_run_id=run_id)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(command)

        assert EXECUTION_STATUS_FAILED in exc_info.value.message

    async def test_pause_non_pausable_run_emits_no_events(self) -> None:
        # Arrange
        run_id = "run-completed-002"
        use_case, fake_store, fake_bus = _make_use_case()
        completed_state = _make_run_state(
            pipeline_run_id=run_id,
            stage=PipelineStage.COMPLETED,
        )
        await fake_store.save_state(completed_state)
        command = PauseCommand(pipeline_run_id=run_id)

        # Act
        with pytest.raises(ValidationError):
            await use_case.execute(command)

        # Assert
        assert fake_bus.events_by_name("pipeline.run_paused") == []


class TestPauseNonExistentRun:
    async def test_pause_nonexistent_run_raises_validation_error(self) -> None:
        # Arrange
        run_id = "run-does-not-exist"
        use_case, _, _ = _make_use_case()
        command = PauseCommand(pipeline_run_id=run_id)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await use_case.execute(command)

        assert run_id in exc_info.value.message
        assert "not found" in exc_info.value.message

    async def test_pause_nonexistent_run_emits_no_events(self) -> None:
        # Arrange
        run_id = "run-ghost"
        use_case, _, fake_bus = _make_use_case()
        command = PauseCommand(pipeline_run_id=run_id)

        # Act
        with pytest.raises(ValidationError):
            await use_case.execute(command)

        # Assert
        assert fake_bus.published_events == []
