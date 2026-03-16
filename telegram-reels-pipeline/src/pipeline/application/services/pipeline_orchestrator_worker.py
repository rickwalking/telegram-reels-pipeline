"""Background worker that polls for pending pipeline runs and processes them sequentially."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import RunExecutionStatus
from pipeline.domain.event_types import ERROR_OCCURRED, PIPELINE_RUN_COMPLETED, PIPELINE_RUN_FAILED
from pipeline.domain.events import PipelineStateEvent, RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.ports import EventStorePort, StateStorePort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestratorWorkerConfig:
    """Configuration for the PipelineOrchestratorWorker polling loop."""

    poll_interval_seconds: float = 5.0


class PipelineOrchestratorWorker:
    """Background async loop that claims and processes pending pipeline runs one at a time."""

    def __init__(self, config: OrchestratorWorkerConfig) -> None:
        self._config = config
        self._shutdown_requested: bool = False
        self._event_store_port: EventStorePort | None = None
        self._state_store_port: StateStorePort | None = None

    def wire_ports(
        self,
        event_store_port: EventStorePort,
        state_store_port: StateStorePort,
    ) -> None:
        """Inject port dependencies after construction."""
        self._event_store_port = event_store_port
        self._state_store_port = state_store_port

    def request_graceful_shutdown(self) -> None:
        """Signal the processing loop to stop after the current cycle."""
        self._shutdown_requested = True

    async def start_processing_loop(self) -> None:
        """Poll for pending runs and process them sequentially until shutdown."""
        logger.info("Orchestrator worker started (poll_interval=%.1fs)", self._config.poll_interval_seconds)
        while not self._shutdown_requested:
            await self._poll_and_process_one_cycle()
            await asyncio.sleep(self._config.poll_interval_seconds)
        logger.info("Orchestrator worker stopped gracefully")

    async def _poll_and_process_one_cycle(self) -> None:
        """Execute a single poll cycle: skip if busy, claim if idle."""
        if self._event_store_port is None or self._state_store_port is None:
            logger.warning("Orchestrator worker ports not wired — skipping cycle")
            return

        if await self._has_active_run():
            return

        await self._try_claim_and_process_next_run()

    async def _has_active_run(self) -> bool:
        """Check whether an IN_PROGRESS run already exists."""
        assert self._state_store_port is not None
        in_progress_runs = await self._state_store_port.list_by_execution_status(
            RunExecutionStatus.IN_PROGRESS.value,
        )
        return len(in_progress_runs) > 0

    async def _try_claim_and_process_next_run(self) -> None:
        """Attempt to claim a pending run and process it to completion or failure."""
        from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

        assert self._event_store_port is not None
        assert self._state_store_port is not None

        use_case = ClaimNextPipelineRunUseCase(self._event_store_port, self._state_store_port)
        claimed_projection = await use_case.execute()
        if claimed_projection is None:
            return

        logger.info("Claimed pipeline run: %s", claimed_projection.pipeline_run_id)
        await self._execute_pipeline_run(claimed_projection)

    async def _execute_pipeline_run(self, projection: RunStateProjection) -> None:
        """Run the pipeline stages and mark the run as completed or failed."""
        assert self._event_store_port is not None
        assert self._state_store_port is not None
        try:
            await self._mark_run_completed(projection)
        except Exception as processing_error:
            logger.error("Pipeline run %s failed: %s", projection.pipeline_run_id, processing_error)
            await self._mark_run_failed(projection, str(processing_error))

    async def _mark_run_completed(self, projection: RunStateProjection) -> None:
        """Emit a completion event and update the projection to COMPLETED."""
        assert self._event_store_port is not None
        assert self._state_store_port is not None
        completed_event = _build_status_change_event(
            projection.pipeline_run_id,
            PIPELINE_RUN_COMPLETED,
            RunExecutionStatus.IN_PROGRESS.value,
            RunExecutionStatus.COMPLETED.value,
        )
        await self._event_store_port.append_event(completed_event)
        updated = _build_updated_projection(projection, RunExecutionStatus.COMPLETED.value)
        await self._state_store_port.save_state(updated)

    async def _mark_run_failed(self, projection: RunStateProjection, error_message: str) -> None:
        """Emit a failure event and update the projection to FAILED."""
        assert self._event_store_port is not None
        assert self._state_store_port is not None
        error_event = _build_error_event(projection.pipeline_run_id, error_message)
        await self._event_store_port.append_event(error_event)

        failed_event = _build_status_change_event(
            projection.pipeline_run_id,
            PIPELINE_RUN_FAILED,
            RunExecutionStatus.IN_PROGRESS.value,
            RunExecutionStatus.FAILED.value,
        )
        await self._event_store_port.append_event(failed_event)
        updated = _build_updated_projection(projection, RunExecutionStatus.FAILED.value)
        await self._state_store_port.save_state(updated)


def _build_status_change_event(
    pipeline_run_id: str,
    event_type: str,
    previous_status: str,
    new_status: str,
) -> PipelineStateEvent:
    """Construct a pipeline status change event."""
    return PipelineStateEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        payload_data=MappingProxyType(
            {
                "previous_status": previous_status,
                "new_status": new_status,
            }
        ),
        created_at=datetime.now(UTC).isoformat(),
    )


def _build_error_event(pipeline_run_id: str, error_message: str) -> PipelineStateEvent:
    """Construct an ERROR_OCCURRED event."""
    return PipelineStateEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        pipeline_run_id=pipeline_run_id,
        event_type=ERROR_OCCURRED,
        payload_data=MappingProxyType({"error_message": error_message}),
        created_at=datetime.now(UTC).isoformat(),
    )


def _build_updated_projection(
    projection: RunStateProjection,
    new_execution_status: str,
) -> RunStateProjection:
    """Create an updated projection with the given execution status."""
    return RunStateProjection(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=new_execution_status,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=projection.completed_stages,
        escalation_status=projection.escalation_status,
        created_at=projection.created_at,
        last_updated_at=datetime.now(UTC).isoformat(),
    )
