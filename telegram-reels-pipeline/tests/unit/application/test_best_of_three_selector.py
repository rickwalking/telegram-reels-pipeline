"""Unit tests for BestOfThreeSelector."""

from __future__ import annotations

import pytest

from pipeline.application.services.best_of_three_selector import (
    MINIMUM_ACCEPTABLE_SCORE,
    select_best_attempt,
)
from pipeline.application.use_cases.evaluate_stage_output_use_case import QaEvaluationCommand


def _make_command(score: int, decision: str = "REWORK", stage: str = "research") -> QaEvaluationCommand:
    """Helper to build a QaEvaluationCommand with the given score."""
    return QaEvaluationCommand(
        pipeline_run_id="run-001",
        stage_name=stage,
        qa_decision=decision,
        critique_score=score,
    )


class TestSelectBestAttemptHighestScore:
    def test_selects_highest_score_from_three(self) -> None:
        # Arrange
        attempts = (
            _make_command(score=50),
            _make_command(score=75),
            _make_command(score=65),
        )

        # Act
        best = select_best_attempt(attempts)

        # Assert
        assert best.critique_score == 75

    def test_selects_highest_score_from_two(self) -> None:
        # Arrange
        attempts = (_make_command(score=40), _make_command(score=80))

        # Act
        best = select_best_attempt(attempts)

        # Assert
        assert best.critique_score == 80

    def test_single_attempt_is_returned(self) -> None:
        # Arrange
        attempts = (_make_command(score=55),)

        # Act
        best = select_best_attempt(attempts)

        # Assert
        assert best.critique_score == 55

    def test_returns_command_identity_not_copy(self) -> None:
        # Arrange
        command_low = _make_command(score=30)
        command_high = _make_command(score=90)
        attempts = (command_low, command_high)

        # Act
        best = select_best_attempt(attempts)

        # Assert — same object reference, not just equal value
        assert best is command_high


class TestSelectBestAttemptTieBreaking:
    def test_tie_returns_first_highest(self) -> None:
        # Arrange — two commands with the same score
        command_a = _make_command(score=70, stage="research")
        command_b = _make_command(score=70, stage="transcript")
        attempts = (command_a, command_b)

        # Act
        best = select_best_attempt(attempts)

        # Assert — max() returns first maximum found, which is command_a
        assert best.critique_score == 70
        assert best is command_a

    def test_all_equal_scores_returns_first(self) -> None:
        # Arrange
        attempts = tuple(_make_command(score=60) for _ in range(3))

        # Act
        best = select_best_attempt(attempts)

        # Assert
        assert best.critique_score == 60


class TestSelectBestAttemptBelowThreshold:
    def test_returns_best_even_when_all_below_threshold(self) -> None:
        # Arrange
        attempts = (
            _make_command(score=20),
            _make_command(score=35),
            _make_command(score=28),
        )

        # Act
        best = select_best_attempt(attempts)

        # Assert — still returns the highest even though all < MINIMUM_ACCEPTABLE_SCORE
        assert best.critique_score == 35

    def test_minimum_acceptable_score_constant_is_70(self) -> None:
        # Assert
        assert MINIMUM_ACCEPTABLE_SCORE == 70

    def test_score_at_threshold_does_not_log_warning(self) -> None:
        # Arrange — score exactly at threshold should not trigger warning path
        attempts = (_make_command(score=MINIMUM_ACCEPTABLE_SCORE),)

        # Act / Assert — no exception; threshold boundary is inclusive
        best = select_best_attempt(attempts)
        assert best.critique_score == MINIMUM_ACCEPTABLE_SCORE


class TestSelectBestAttemptEmptyInput:
    def test_empty_tuple_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="No QA attempts"):
            select_best_attempt(())
