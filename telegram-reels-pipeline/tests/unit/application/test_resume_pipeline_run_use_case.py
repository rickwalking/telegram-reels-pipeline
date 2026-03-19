"""Unit tests for ResumePipelineRunUseCase."""

from __future__ import annotations

import pytest

from pipeline.application.services.pipeline_event_emitter_service import (
    PipelineEventEmitterService,
)
from pipeline.application.use_cases.resume_pipeline_run_use_case import (
    PipelineRunNotFoundError,
    PipelineRunNotResumableError,
    ResumeCommand,
    ResumePipelineRunUseCase,
)
from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.event_types import RunStateProjection
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeStateStore:
    """In-memory fake implementing StateStorePort for unit tests."""

    def __init__(self, stored_state: RunState | None = None) -> None:
        self._stored_state = stored_state
        self.saved: list[RunState] = []

    async def save_state(self, state: RunState) -> None:
        """Record saved states for assertion."""
        self.saved.append(state)
        self._stored_state = state

    async def load_state(self, run_id: RunId) -> RunState | None:
        """Return stored state if run_id matches."""
        if self._stored_state and self._stored_state.run_id == run_id:
            return self._stored_state
        return None

    async def list_incomplete_runs(self) -> list[RunState]:
        """Return empty list — not used in resume tests."""
        return []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_paused_run_state(
    run_id: str = "run-paused-001",
    stage: PipelineStage = PipelineStage.FFMPEG_ENGINEER,
    stages_completed: tuple[str, ...] = ("router", "research", "transcript", "content", "layout_detective"),
) -> RunState:
    """Build a RunState that represents a paused pipeline run."""
    return RunState(
        run_id=RunId(run_id),
        youtube_url="https://www.youtube.com/watch?v=test123",
        current_stage=stage,
        current_attempt=1,
        qa_status=QAStatus.PENDING,
        stages_completed=stages_completed,
        escalation_state=EscalationState.QA_EXHAUSTED,
        created_at="2026-03-10T10:00:00Z",
        updated_at="2026-03-10T11:00:00Z",
    )


def _make_running_run_state(
    run_id: str = "run-running-001",
) -> RunState:
    """Build a RunState that represents an actively running pipeline run."""
    return RunState(
        run_id=RunId(run_id),
        youtube_url="https://www.youtube.com/watch?v=running456",
        current_stage=PipelineStage.RESEARCH,
        current_attempt=1,
        qa_status=QAStatus.PENDING,
        stages_completed=("router",),
        escalation_state=EscalationState.NONE,
        created_at="2026-03-10T10:00:00Z",
        updated_at="2026-03-10T10:05:00Z",
    )


def _make_use_case(stored_state: RunState | None) -> tuple[ResumePipelineRunUseCase, FakeStateStore]:
    """Build a ResumePipelineRunUseCase with fake dependencies."""
    state_store = FakeStateStore(stored_state=stored_state)
    event_emitter = PipelineEventEmitterService(state_store=state_store)
    use_case = ResumePipelineRunUseCase(
        state_store=state_store,
        event_emitter=event_emitter,
    )
    return use_case, state_store


# ---------------------------------------------------------------------------
# ResumeCommand validation tests
# ---------------------------------------------------------------------------


class TestResumeCommand:
    def test_raises_when_pipeline_run_id_is_empty(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id must not be empty"):
            ResumeCommand(pipeline_run_id="")

    def test_accepts_valid_command_with_defaults(self) -> None:
        # Arrange / Act
        command = ResumeCommand(pipeline_run_id="run-001")

        # Assert
        assert command.pipeline_run_id == "run-001"
        assert command.resume_from_stage == ""
        assert command.operator_notes == ""

    def test_accepts_optional_fields(self) -> None:
        # Arrange / Act
        command = ResumeCommand(
            pipeline_run_id="run-001",
            resume_from_stage="research",
            operator_notes="Manual override",
        )

        # Assert
        assert command.resume_from_stage == "research"
        assert command.operator_notes == "Manual override"


# ---------------------------------------------------------------------------
# ResumePipelineRunUseCase.execute tests — happy path
# ---------------------------------------------------------------------------


class TestResumePipelineRunUseCaseSuccess:
    async def test_returns_projection_with_running_status_for_paused_run(self) -> None:
        # Arrange
        paused_state = _make_paused_run_state()
        use_case, _store = _make_use_case(stored_state=paused_state)

        # The emitter must think the run is paused — we need to override projection
        # by patching the state to indicate paused execution status
        # Since our emitter derives status from stage (not escalation),
        # we test the full flow: paused state returns paused projection,
        # and after resume it returns running projection.
        # For this test, we directly force the emitter to see "paused" status.

        # We simulate a paused run by overriding emit_pipeline_resumed logic
        # via a custom projection override in the fake emitter.
        from pipeline.application.services.pipeline_event_emitter_service import (
            PipelineEventEmitterService,
        )

        class FakePausedEmitter(PipelineEventEmitterService):
            """Emitter that always reports paused status for the initial projection."""

            async def project_run_state(self, run_state: RunState) -> RunStateProjection:
                return RunStateProjection(
                    pipeline_run_id=str(run_state.run_id),
                    execution_status="paused",
                    current_stage=run_state.current_stage.value,
                    stages_completed=run_state.stages_completed,
                )

        state_store = FakeStateStore(stored_state=paused_state)
        emitter = FakePausedEmitter(state_store=state_store)
        use_case_with_fake_emitter = ResumePipelineRunUseCase(
            state_store=state_store,
            event_emitter=emitter,
        )
        command = ResumeCommand(pipeline_run_id="run-paused-001")

        # Act
        projection = await use_case_with_fake_emitter.execute(command)

        # Assert
        assert projection.pipeline_run_id == "run-paused-001"
        assert projection.execution_status == "running"

    async def test_propagates_operator_notes_to_projection(self) -> None:
        # Arrange
        paused_state = _make_paused_run_state()
        state_store = FakeStateStore(stored_state=paused_state)

        from pipeline.application.services.pipeline_event_emitter_service import (
            PipelineEventEmitterService,
        )

        class FakePausedEmitter(PipelineEventEmitterService):
            async def project_run_state(self, run_state: RunState) -> RunStateProjection:
                return RunStateProjection(
                    pipeline_run_id=str(run_state.run_id),
                    execution_status="paused",
                    current_stage=run_state.current_stage.value,
                    stages_completed=run_state.stages_completed,
                )

        emitter = FakePausedEmitter(state_store=state_store)
        use_case = ResumePipelineRunUseCase(state_store=state_store, event_emitter=emitter)
        command = ResumeCommand(
            pipeline_run_id="run-paused-001",
            operator_notes="Resuming after manual QA review",
        )

        # Act
        projection = await use_case.execute(command)

        # Assert
        assert projection.operator_notes == "Resuming after manual QA review"

    async def test_returned_projection_has_correct_stages_completed(self) -> None:
        # Arrange
        completed = ("router", "research", "transcript", "content", "layout_detective")
        paused_state = _make_paused_run_state(stages_completed=completed)
        state_store = FakeStateStore(stored_state=paused_state)

        from pipeline.application.services.pipeline_event_emitter_service import (
            PipelineEventEmitterService,
        )

        class FakePausedEmitter(PipelineEventEmitterService):
            async def project_run_state(self, run_state: RunState) -> RunStateProjection:
                return RunStateProjection(
                    pipeline_run_id=str(run_state.run_id),
                    execution_status="paused",
                    current_stage=run_state.current_stage.value,
                    stages_completed=run_state.stages_completed,
                )

        emitter = FakePausedEmitter(state_store=state_store)
        use_case = ResumePipelineRunUseCase(state_store=state_store, event_emitter=emitter)
        command = ResumeCommand(pipeline_run_id="run-paused-001")

        # Act
        projection = await use_case.execute(command)

        # Assert
        assert projection.stages_completed == completed


# ---------------------------------------------------------------------------
# ResumePipelineRunUseCase.execute tests — error paths
# ---------------------------------------------------------------------------


class TestResumePipelineRunUseCaseErrors:
    async def test_raises_not_found_when_run_does_not_exist(self) -> None:
        # Arrange
        use_case, _store = _make_use_case(stored_state=None)
        command = ResumeCommand(pipeline_run_id="nonexistent-run-id")

        # Act / Assert
        with pytest.raises(PipelineRunNotFoundError, match="not found"):
            await use_case.execute(command)

    async def test_raises_not_resumable_when_run_is_already_running(self) -> None:
        # Arrange
        running_state = _make_running_run_state()
        use_case, _store = _make_use_case(stored_state=running_state)
        command = ResumeCommand(pipeline_run_id="run-running-001")

        # Act / Assert
        with pytest.raises(PipelineRunNotResumableError, match="cannot be resumed"):
            await use_case.execute(command)

    async def test_raises_not_resumable_when_run_is_completed(self) -> None:
        # Arrange
        completed_state = RunState(
            run_id=RunId("run-completed-001"),
            youtube_url="https://www.youtube.com/watch?v=done",
            current_stage=PipelineStage.COMPLETED,
            current_attempt=1,
            qa_status=QAStatus.PASSED,
            stages_completed=("router", "research"),
            escalation_state=EscalationState.NONE,
            created_at="2026-03-10T10:00:00Z",
            updated_at="2026-03-10T12:00:00Z",
        )
        use_case, _store = _make_use_case(stored_state=completed_state)
        command = ResumeCommand(pipeline_run_id="run-completed-001")

        # Act / Assert
        with pytest.raises(PipelineRunNotResumableError, match="cannot be resumed"):
            await use_case.execute(command)

    async def test_raises_not_resumable_when_run_is_failed(self) -> None:
        # Arrange
        failed_state = RunState(
            run_id=RunId("run-failed-001"),
            youtube_url="https://www.youtube.com/watch?v=fail",
            current_stage=PipelineStage.FAILED,
            current_attempt=3,
            qa_status=QAStatus.FAILED,
            stages_completed=("router",),
            escalation_state=EscalationState.ERROR_ESCALATED,
            created_at="2026-03-10T10:00:00Z",
            updated_at="2026-03-10T10:30:00Z",
        )
        use_case, _store = _make_use_case(stored_state=failed_state)
        command = ResumeCommand(pipeline_run_id="run-failed-001")

        # Act / Assert
        with pytest.raises(PipelineRunNotResumableError, match="cannot be resumed"):
            await use_case.execute(command)
