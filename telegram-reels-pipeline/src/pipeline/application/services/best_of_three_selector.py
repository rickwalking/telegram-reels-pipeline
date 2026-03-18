"""BestOfThreeSelector — pure selection of the highest-scoring QA attempt."""

from __future__ import annotations

import logging

from pipeline.application.use_cases.evaluate_stage_output_use_case import QaEvaluationCommand

logger = logging.getLogger(__name__)

# Minimum acceptable score — attempts below this are flagged even when selected as best
MINIMUM_ACCEPTABLE_SCORE: int = 70


def select_best_attempt(attempts: tuple[QaEvaluationCommand, ...]) -> QaEvaluationCommand:
    """Return the QaEvaluationCommand with the highest critique_score.

    When all scores fall below MINIMUM_ACCEPTABLE_SCORE the best attempt is
    still returned (caller must inspect the score to decide on escalation).
    Raises ValueError if the attempts tuple is empty.

    Pure function — no I/O, no side effects, fully deterministic.
    """
    if not attempts:
        raise ValueError("No QA attempts to select from")
    best = max(attempts, key=lambda command: command.critique_score)
    if best.critique_score < MINIMUM_ACCEPTABLE_SCORE:
        logger.warning(
            "Best QA attempt score %d is below threshold %d for stage '%s' — escalation may be needed",
            best.critique_score,
            MINIMUM_ACCEPTABLE_SCORE,
            best.stage_name,
        )
    return best
