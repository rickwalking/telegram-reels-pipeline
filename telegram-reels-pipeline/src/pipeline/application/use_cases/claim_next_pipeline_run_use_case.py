"""Application use case: claim the next pending pipeline run from the FIFO queue."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import RunExecutionStatus
from pipeline.domain.event_types import PIPELINE_RUN_CLAIMED
from pipeline.domain.events import PipelineStateEvent, RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.ports import EventStorePort, StateStorePort


class ClaimNextPipelineRunUseCase:
    """Claim the oldest PENDING run and transition it to IN_PROGRESS."""

    def __init__(
        self,
        event_store_port: EventStorePort,
        state_store_port: StateStorePort,
    ) -> None:
        self._event_store_port = event_store_port
        self._state_store_port = state_store_port

    async def execute(self) -> RunStateProjection | None:
        """Find the oldest PENDING run, emit a claimed event, and update the projection."""
        pending_runs = await self._state_store_port.list_by_execution_status(
            RunExecutionStatus.PENDING.value,
        )
        if not pending_runs:
            return None

        oldest_pending_run = _select_oldest_pending_run(pending_runs)
        claimed_event = _build_claimed_event(oldest_pending_run)
        await self._event_store_port.append_event(claimed_event)

        updated_projection = _build_in_progress_projection(oldest_pending_run)
        await self._state_store_port.save_state(updated_projection)
        return updated_projection


def _select_oldest_pending_run(pending_runs: list[RunStateProjection]) -> RunStateProjection:
    """Return the run with the earliest created_at timestamp (FIFO order)."""
    return min(pending_runs, key=lambda run: run.created_at)


def _build_claimed_event(projection: RunStateProjection) -> PipelineStateEvent:
    """Construct a PIPELINE_RUN_CLAIMED event for the given projection."""
    return PipelineStateEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        pipeline_run_id=projection.pipeline_run_id,
        event_type=PIPELINE_RUN_CLAIMED,
        stage_name=projection.current_stage,
        payload_data=MappingProxyType(
            {
                "previous_status": RunExecutionStatus.PENDING.value,
                "new_status": RunExecutionStatus.IN_PROGRESS.value,
            }
        ),
        created_at=datetime.now(UTC).isoformat(),
    )


def _build_in_progress_projection(projection: RunStateProjection) -> RunStateProjection:
    """Create an updated projection with IN_PROGRESS execution status."""
    return RunStateProjection(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=RunExecutionStatus.IN_PROGRESS.value,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=projection.completed_stages,
        escalation_status=projection.escalation_status,
        created_at=projection.created_at,
        last_updated_at=datetime.now(UTC).isoformat(),
    )
