"""CrashRecoveryHandler — detect and resume interrupted pipeline runs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage
from pipeline.domain.transitions import STAGE_ORDER

if TYPE_CHECKING:
    from pipeline.domain.models import RunState
    from pipeline.domain.ports import MessagingPort, StateStorePort

logger = logging.getLogger(__name__)

# Map stage value strings to PipelineStage for lookup
_STAGE_BY_VALUE: dict[str, PipelineStage] = {s.value: s for s in PipelineStage}


@dataclass(frozen=True)
class RecoveryPlan:
    """Describes how to resume an interrupted run."""

    run_state: RunState
    resume_from: PipelineStage
    stages_remaining: tuple[PipelineStage, ...]
    stages_already_done: int


class CrashRecoveryHandler:
    """Detect incomplete runs at startup and build recovery plans.

    Uses StateStorePort to scan for in-progress runs and determines the
    correct stage to resume from based on stages_completed metadata.
    """

    def __init__(
        self,
        state_store: StateStorePort,
        messaging: MessagingPort | None = None,
    ) -> None:
        self._state_store = state_store
        self._messaging = messaging

    async def scan_and_recover(self) -> tuple[RecoveryPlan, ...]:
        """Scan for interrupted runs and return recovery plans.

        For each incomplete run found, determines the correct resume point
        and notifies the user via Telegram.
        """
        incomplete = await self._state_store.list_incomplete_runs()
        if not incomplete:
            logger.info("No interrupted runs found — clean startup")
            return ()

        plans: list[RecoveryPlan] = []
        for run_state in incomplete:
            plan = _build_recovery_plan(run_state)
            if plan is not None:
                plans.append(plan)
                await self._notify_resume(plan)

        logger.info("Found %d interrupted run(s) to resume", len(plans))
        return tuple(plans)

    async def _notify_resume(self, plan: RecoveryPlan) -> None:
        """Send a Telegram notification about the resumed run."""
        if self._messaging is None:
            return

        total = len(STAGE_ORDER)
        msg = (
            f"Resuming your run from {plan.resume_from.value} "
            f"({plan.stages_already_done} of {total} stages already completed)"
        )
        try:
            await self._messaging.notify_user(msg)
        except Exception:
            logger.exception("Failed to send recovery notification for run %s", plan.run_state.run_id)


def _build_recovery_plan(run_state: RunState) -> RecoveryPlan | None:
    """Determine the resume point from a run's completed stages.

    Returns None if the run state is inconsistent (no valid resume point).
    """
    # Only count recognized stage values
    known_values = {s.value for s in STAGE_ORDER}
    completed_set = set(run_state.stages_completed) & known_values

    # Find the first stage in STAGE_ORDER not yet completed
    resume_from: PipelineStage | None = None
    remaining: list[PipelineStage] = []
    for stage in STAGE_ORDER:
        if stage.value not in completed_set:
            if resume_from is None:
                resume_from = stage
            remaining.append(stage)

    if resume_from is None:
        logger.warning(
            "Run %s has all stages completed but is not terminal — skipping",
            run_state.run_id,
        )
        return None

    return RecoveryPlan(
        run_state=run_state,
        resume_from=resume_from,
        stages_remaining=tuple(remaining),
        stages_already_done=len(completed_set),
    )
