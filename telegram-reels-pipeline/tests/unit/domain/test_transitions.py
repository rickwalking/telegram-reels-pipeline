"""Tests for FSM transition table — completeness, reachability, and guard logic."""

from pipeline.domain.enums import PipelineStage
from pipeline.domain.transitions import (
    MAX_QA_ATTEMPTS,
    STAGE_ORDER,
    TERMINAL_STAGES,
    TRANSITIONS,
    get_next_stage,
    is_terminal,
    is_valid_transition,
)


class TestTransitionTable:
    def test_all_processing_stages_have_qa_pass_transition(self) -> None:
        """Every processing stage (except DELIVERY) must have a qa_pass transition."""
        for stage in STAGE_ORDER:
            if stage == PipelineStage.DELIVERY:
                continue
            assert (stage, "qa_pass") in TRANSITIONS, f"{stage.name} missing qa_pass transition"

    def test_delivery_has_stage_complete(self) -> None:
        assert (PipelineStage.DELIVERY, "stage_complete") in TRANSITIONS

    def test_qa_pass_progresses_forward(self) -> None:
        """qa_pass on each stage leads to the NEXT stage in STAGE_ORDER."""
        for i, stage in enumerate(STAGE_ORDER[:-1]):  # exclude DELIVERY
            next_stage = TRANSITIONS[(stage, "qa_pass")]
            expected_next = STAGE_ORDER[i + 1]
            assert (
                next_stage == expected_next
            ), f"{stage.name} qa_pass -> {next_stage.name}, expected {expected_next.name}"

    def test_qa_rework_stays_on_same_stage(self) -> None:
        for stage in STAGE_ORDER:
            if stage == PipelineStage.DELIVERY:
                continue
            assert TRANSITIONS.get((stage, "qa_rework")) == stage

    def test_qa_fail_stays_on_same_stage(self) -> None:
        for stage in STAGE_ORDER:
            if stage == PipelineStage.DELIVERY:
                continue
            assert TRANSITIONS.get((stage, "qa_fail")) == stage

    def test_terminal_stages_have_no_outgoing_transitions(self) -> None:
        for stage in TERMINAL_STAGES:
            outgoing = [(s, e) for (s, e) in TRANSITIONS if s == stage]
            assert outgoing == [], f"Terminal stage {stage.name} has outgoing transitions"

    def test_all_stages_reachable_via_qa_pass(self) -> None:
        """Starting from ROUTER with qa_pass, every stage in STAGE_ORDER is reachable."""
        current = PipelineStage.ROUTER
        visited = [current]
        for _ in range(len(STAGE_ORDER)):
            event = "qa_pass" if current != PipelineStage.DELIVERY else "stage_complete"
            next_stage = TRANSITIONS.get((current, event))
            if next_stage is None:
                break
            visited.append(next_stage)
            current = next_stage
        assert PipelineStage.COMPLETED in visited


class TestFailureTransitions:
    def test_all_processing_stages_have_unrecoverable_error(self) -> None:
        """Every processing stage must transition to FAILED on unrecoverable_error."""
        for stage in STAGE_ORDER:
            assert (stage, "unrecoverable_error") in TRANSITIONS, f"{stage.name} missing unrecoverable_error transition"
            assert TRANSITIONS[(stage, "unrecoverable_error")] == PipelineStage.FAILED

    def test_failed_is_reachable(self) -> None:
        """FAILED state must be reachable via unrecoverable_error from any stage."""
        for stage in STAGE_ORDER:
            next_stage = get_next_stage(stage, "unrecoverable_error")
            assert next_stage == PipelineStage.FAILED


class TestStageOrder:
    def test_stage_order_length(self) -> None:
        assert len(STAGE_ORDER) == 8

    def test_starts_with_router(self) -> None:
        assert STAGE_ORDER[0] == PipelineStage.ROUTER

    def test_ends_with_delivery(self) -> None:
        assert STAGE_ORDER[-1] == PipelineStage.DELIVERY

    def test_no_terminal_stages_in_order(self) -> None:
        for stage in STAGE_ORDER:
            assert stage not in TERMINAL_STAGES


class TestTerminalStages:
    def test_completed_is_terminal(self) -> None:
        assert is_terminal(PipelineStage.COMPLETED)

    def test_failed_is_terminal(self) -> None:
        assert is_terminal(PipelineStage.FAILED)

    def test_router_is_not_terminal(self) -> None:
        assert not is_terminal(PipelineStage.ROUTER)


class TestHelperFunctions:
    def test_is_valid_transition_true(self) -> None:
        assert is_valid_transition(PipelineStage.ROUTER, "qa_pass")

    def test_is_valid_transition_false(self) -> None:
        assert not is_valid_transition(PipelineStage.COMPLETED, "qa_pass")

    def test_get_next_stage_valid(self) -> None:
        assert get_next_stage(PipelineStage.ROUTER, "qa_pass") == PipelineStage.RESEARCH

    def test_get_next_stage_invalid_returns_none(self) -> None:
        assert get_next_stage(PipelineStage.COMPLETED, "qa_pass") is None


class TestConstants:
    def test_max_qa_attempts(self) -> None:
        assert MAX_QA_ATTEMPTS == 3
