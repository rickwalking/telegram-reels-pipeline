"""Tests for FSM transition table — completeness, reachability, and guard logic."""

from pipeline.domain.enums import FramingStyleState, PipelineStage
from pipeline.domain.transitions import (
    FRAMING_EVENTS,
    FRAMING_TRANSITIONS,
    MAX_QA_ATTEMPTS,
    STAGE_ORDER,
    TERMINAL_STAGES,
    TRANSITIONS,
    get_framing_state,
    get_next_stage,
    is_terminal,
    is_valid_framing_transition,
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


class TestFramingTransitions:
    def test_solo_to_duo_split_on_face_increase(self) -> None:
        assert get_framing_state(FramingStyleState.SOLO, "face_count_increase") == FramingStyleState.DUO_SPLIT

    def test_duo_split_to_solo_on_face_decrease(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_SPLIT, "face_count_decrease") == FramingStyleState.SOLO

    def test_duo_pip_to_solo_on_face_decrease(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_PIP, "face_count_decrease") == FramingStyleState.SOLO

    def test_duo_split_to_pip_on_request(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_SPLIT, "pip_requested") == FramingStyleState.DUO_PIP

    def test_duo_pip_to_split_on_request(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_PIP, "split_requested") == FramingStyleState.DUO_SPLIT

    def test_solo_to_screen_share(self) -> None:
        assert get_framing_state(FramingStyleState.SOLO, "screen_share_detected") == FramingStyleState.SCREEN_SHARE

    def test_duo_split_to_screen_share(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_SPLIT, "screen_share_detected") == FramingStyleState.SCREEN_SHARE

    def test_duo_pip_to_screen_share(self) -> None:
        assert get_framing_state(FramingStyleState.DUO_PIP, "screen_share_detected") == FramingStyleState.SCREEN_SHARE

    def test_screen_share_to_duo_split_on_face_increase(self) -> None:
        assert get_framing_state(FramingStyleState.SCREEN_SHARE, "face_count_increase") == FramingStyleState.DUO_SPLIT

    def test_screen_share_to_solo_on_end(self) -> None:
        assert get_framing_state(FramingStyleState.SCREEN_SHARE, "screen_share_ended") == FramingStyleState.SOLO

    def test_solo_to_cinematic_on_request(self) -> None:
        assert get_framing_state(FramingStyleState.SOLO, "cinematic_requested") == FramingStyleState.CINEMATIC_SOLO

    def test_cinematic_to_duo_split_on_face_increase(self) -> None:
        assert get_framing_state(FramingStyleState.CINEMATIC_SOLO, "face_count_increase") == FramingStyleState.DUO_SPLIT

    def test_cinematic_to_screen_share(self) -> None:
        result = get_framing_state(FramingStyleState.CINEMATIC_SOLO, "screen_share_detected")
        assert result == FramingStyleState.SCREEN_SHARE

    def test_invalid_transition_returns_none(self) -> None:
        assert get_framing_state(FramingStyleState.SOLO, "pip_requested") is None

    def test_is_valid_framing_transition_true(self) -> None:
        assert is_valid_framing_transition(FramingStyleState.SOLO, "face_count_increase")

    def test_is_valid_framing_transition_false(self) -> None:
        assert not is_valid_framing_transition(FramingStyleState.SOLO, "nonexistent_event")

    def test_all_transition_keys_use_valid_events(self) -> None:
        for _state, event in FRAMING_TRANSITIONS:
            assert event in FRAMING_EVENTS, f"Event '{event}' not in FRAMING_EVENTS"

    def test_all_transition_values_are_framing_states(self) -> None:
        for target in FRAMING_TRANSITIONS.values():
            assert isinstance(target, FramingStyleState)

    def test_framing_events_count(self) -> None:
        assert len(FRAMING_EVENTS) == 7

    def test_round_trip_solo_duo_solo(self) -> None:
        """Solo -> face increase -> DUO_SPLIT -> face decrease -> Solo."""
        state = FramingStyleState.SOLO
        state = get_framing_state(state, "face_count_increase")
        assert state == FramingStyleState.DUO_SPLIT
        state = get_framing_state(state, "face_count_decrease")
        assert state == FramingStyleState.SOLO

    def test_round_trip_duo_modes(self) -> None:
        """DUO_SPLIT -> pip -> DUO_PIP -> split -> DUO_SPLIT."""
        state = FramingStyleState.DUO_SPLIT
        state = get_framing_state(state, "pip_requested")
        assert state == FramingStyleState.DUO_PIP
        state = get_framing_state(state, "split_requested")
        assert state == FramingStyleState.DUO_SPLIT

    def test_screen_share_to_duo_via_two_events(self) -> None:
        """0→2 boundary: screen_share_ended then face_count_increase."""
        state = FramingStyleState.SCREEN_SHARE
        state = get_framing_state(state, "screen_share_ended")
        assert state == FramingStyleState.SOLO
        state = get_framing_state(state, "face_count_increase")
        assert state == FramingStyleState.DUO_SPLIT

    def test_screen_share_to_duo_via_direct_face_increase(self) -> None:
        """0→2 boundary: face_count_increase directly from SCREEN_SHARE."""
        state = FramingStyleState.SCREEN_SHARE
        state = get_framing_state(state, "face_count_increase")
        assert state == FramingStyleState.DUO_SPLIT

    def test_auto_mode_full_scenario(self) -> None:
        """Simulate auto-mode: solo -> duo -> screen_share -> duo -> solo."""
        state = FramingStyleState.SOLO
        # 1 face -> 2 faces
        state = get_framing_state(state, "face_count_increase")
        assert state == FramingStyleState.DUO_SPLIT
        # 2 faces -> 0 faces (screen share)
        state = get_framing_state(state, "screen_share_detected")
        assert state == FramingStyleState.SCREEN_SHARE
        # 0 faces -> 2 faces (direct)
        state = get_framing_state(state, "face_count_increase")
        assert state == FramingStyleState.DUO_SPLIT
        # 2 faces -> 1 face
        state = get_framing_state(state, "face_count_decrease")
        assert state == FramingStyleState.SOLO


class TestConstants:
    def test_max_qa_attempts(self) -> None:
        assert MAX_QA_ATTEMPTS == 3
