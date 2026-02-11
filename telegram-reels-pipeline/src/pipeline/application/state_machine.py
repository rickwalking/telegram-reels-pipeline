"""Pipeline state machine — transition execution with bookkeeping updates."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.errors import ValidationError
from pipeline.domain.models import RunState
from pipeline.domain.transitions import TRANSITIONS, is_terminal, is_valid_transition


class PipelineStateMachine:
    """Applies FSM transitions to RunState, returning a new immutable instance."""

    def validate_transition(self, state: RunState, event: str) -> bool:
        """Check whether a transition is valid without applying it."""
        if is_terminal(state.current_stage):
            return False
        return is_valid_transition(state.current_stage, event)

    def apply_transition(self, state: RunState, event: str) -> RunState:
        """Apply a transition event to the current state, returning new RunState.

        Raises ValidationError if the transition is not defined in the table.
        """
        if is_terminal(state.current_stage):
            raise ValidationError(f"Cannot transition from terminal stage {state.current_stage.value}")

        if not is_valid_transition(state.current_stage, event):
            raise ValidationError(f"Invalid transition: ({state.current_stage.value}, {event})")

        now = datetime.now(UTC).isoformat()

        if event == "qa_pass":
            return replace(
                state,
                current_stage=TRANSITIONS[(state.current_stage, event)],
                stages_completed=state.stages_completed + (state.current_stage.value,),
                current_attempt=1,
                qa_status=QAStatus.PENDING,
                updated_at=now,
            )

        if event == "qa_rework":
            return replace(
                state,
                current_attempt=state.current_attempt + 1,
                qa_status=QAStatus.REWORK,
                updated_at=now,
            )

        if event == "qa_fail":
            return replace(
                state,
                qa_status=QAStatus.FAILED,
                updated_at=now,
            )

        if event == "stage_complete":
            return replace(
                state,
                current_stage=TRANSITIONS[(state.current_stage, event)],
                stages_completed=state.stages_completed + (state.current_stage.value,),
                updated_at=now,
            )

        if event == "unrecoverable_error":
            return replace(
                state,
                current_stage=PipelineStage.FAILED,
                qa_status=QAStatus.FAILED,
                updated_at=now,
            )

        if event == "escalation_requested":
            return replace(
                state,
                escalation_state=EscalationState.LAYOUT_UNKNOWN,
                updated_at=now,
            )

        if event == "escalation_resolved":
            return replace(
                state,
                escalation_state=EscalationState.NONE,
                qa_status=QAStatus.PENDING,
                updated_at=now,
            )

        # Fallback for any future events in the table not yet handled
        return replace(
            state,
            current_stage=TRANSITIONS[(state.current_stage, event)],
            updated_at=now,
        )
