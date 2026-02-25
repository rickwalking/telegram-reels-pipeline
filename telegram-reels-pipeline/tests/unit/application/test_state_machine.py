"""Tests for PipelineStateMachine — transition execution and bookkeeping."""

import pytest

from pipeline.application.state_machine import PipelineStateMachine
from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.errors import ValidationError
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId


@pytest.fixture
def fsm() -> PipelineStateMachine:
    return PipelineStateMachine()


@pytest.fixture
def router_state() -> RunState:
    return RunState(
        run_id=RunId("test-run"),
        youtube_url="https://youtube.com/watch?v=test",
        current_stage=PipelineStage.ROUTER,
        created_at="2026-02-10T14:00:00+00:00",
    )


class TestQAPassTransition:
    def test_advances_to_next_stage(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_pass")
        assert result.current_stage == PipelineStage.RESEARCH

    def test_appends_stage_to_completed(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_pass")
        assert "router" in result.stages_completed

    def test_resets_attempt_to_one(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_pass")
        assert result.current_attempt == 1

    def test_sets_qa_status_pending(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_pass")
        assert result.qa_status == QAStatus.PENDING

    def test_updates_timestamp(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_pass")
        assert result.updated_at != router_state.updated_at
        assert result.updated_at != ""

    def test_full_forward_progression(self, fsm: PipelineStateMachine) -> None:
        """Walk through all stages via qa_pass/stage_complete to verify accumulation."""
        state = RunState(
            run_id=RunId("test"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.ROUTER,
        )
        # (expected_next_stage, event_to_apply)
        steps: list[tuple[PipelineStage, str]] = [
            (PipelineStage.RESEARCH, "qa_pass"),
            (PipelineStage.TRANSCRIPT, "qa_pass"),
            (PipelineStage.CONTENT, "qa_pass"),
            (PipelineStage.LAYOUT_DETECTIVE, "qa_pass"),
            (PipelineStage.FFMPEG_ENGINEER, "qa_pass"),
            (PipelineStage.VEO3_AWAIT, "qa_pass"),
            (PipelineStage.ASSEMBLY, "stage_complete"),
            (PipelineStage.DELIVERY, "qa_pass"),
        ]
        for expected, event in steps:
            state = fsm.apply_transition(state, event)
            assert state.current_stage == expected
        assert len(state.stages_completed) == 8


class TestQAReworkTransition:
    def test_stays_on_same_stage(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_rework")
        assert result.current_stage == PipelineStage.ROUTER

    def test_increments_attempt(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_rework")
        assert result.current_attempt == 2

    def test_sets_qa_status_rework(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_rework")
        assert result.qa_status == QAStatus.REWORK


class TestQAFailTransition:
    def test_stays_on_same_stage(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_fail")
        assert result.current_stage == PipelineStage.ROUTER

    def test_sets_qa_status_failed(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "qa_fail")
        assert result.qa_status == QAStatus.FAILED


class TestStageCompleteTransition:
    def test_delivery_to_completed(self, fsm: PipelineStateMachine) -> None:
        state = RunState(
            run_id=RunId("test"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.DELIVERY,
        )
        result = fsm.apply_transition(state, "stage_complete")
        assert result.current_stage == PipelineStage.COMPLETED
        assert "delivery" in result.stages_completed


class TestUnrecoverableErrorTransition:
    def test_any_stage_to_failed(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "unrecoverable_error")
        assert result.current_stage == PipelineStage.FAILED

    def test_sets_qa_status_failed(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        result = fsm.apply_transition(router_state, "unrecoverable_error")
        assert result.qa_status == QAStatus.FAILED


class TestEscalationTransitions:
    def test_escalation_requested_sets_layout_unknown(self, fsm: PipelineStateMachine) -> None:
        state = RunState(
            run_id=RunId("test"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.LAYOUT_DETECTIVE,
        )
        result = fsm.apply_transition(state, "escalation_requested")
        assert result.escalation_state == EscalationState.LAYOUT_UNKNOWN
        assert result.current_stage == PipelineStage.LAYOUT_DETECTIVE

    def test_escalation_resolved_clears_state(self, fsm: PipelineStateMachine) -> None:
        from dataclasses import replace

        state = replace(
            RunState(
                run_id=RunId("test"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.LAYOUT_DETECTIVE,
            ),
            escalation_state=EscalationState.LAYOUT_UNKNOWN,
        )
        result = fsm.apply_transition(state, "escalation_resolved")
        assert result.escalation_state == EscalationState.NONE
        assert result.qa_status == QAStatus.PENDING


class TestInvalidTransitions:
    def test_invalid_event_raises(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        with pytest.raises(ValidationError, match="Invalid transition"):
            fsm.apply_transition(router_state, "stage_complete")

    def test_terminal_stage_raises(self, fsm: PipelineStateMachine) -> None:
        from dataclasses import replace

        state = replace(
            RunState(
                run_id=RunId("test"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
            ),
            current_stage=PipelineStage.COMPLETED,
        )
        with pytest.raises(ValidationError, match="terminal stage"):
            fsm.apply_transition(state, "qa_pass")

    def test_nonexistent_event_raises(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        with pytest.raises(ValidationError, match="Invalid transition"):
            fsm.apply_transition(router_state, "bogus_event")


class TestValidateTransition:
    def test_valid_returns_true(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        assert fsm.validate_transition(router_state, "qa_pass") is True

    def test_invalid_returns_false(self, fsm: PipelineStateMachine, router_state: RunState) -> None:
        assert fsm.validate_transition(router_state, "stage_complete") is False

    def test_terminal_returns_false(self, fsm: PipelineStateMachine) -> None:
        from dataclasses import replace

        state = replace(
            RunState(
                run_id=RunId("test"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
            ),
            current_stage=PipelineStage.COMPLETED,
        )
        assert fsm.validate_transition(state, "qa_pass") is False
