"""RecoverPipelineRunUseCase — find incomplete runs and replay events to determine resume point."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pipeline.domain.event_types import STAGE_COMPLETED
from pipeline.domain.events import RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.events import PipelineStateEvent
    from pipeline.domain.ports.event_store_port import EventStorePort
    from pipeline.domain.ports.state_store_port import StateStorePort

logger = logging.getLogger(__name__)


def _extract_last_completed_stage(events: list[PipelineStateEvent]) -> str:
    """Find the stage_name of the last STAGE_COMPLETED event in the stream."""
    completed_events = [e for e in events if e.event_type == STAGE_COMPLETED]
    if not completed_events:
        return ""
    return completed_events[-1].stage_name


def _build_recovered_projection(
    pipeline_run_id: str,
    events: list[PipelineStateEvent],
) -> RunStateProjection:
    """Replay events to build a recovered projection with stages completed."""
    completed_stages = tuple(e.stage_name for e in events if e.event_type == STAGE_COMPLETED)
    last_completed = _extract_last_completed_stage(events)
    current_stage = last_completed if last_completed else "router"
    last_event_id = events[-1].event_id if events else ""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        current_stage=current_stage,
        execution_status="recovering",
        stages_completed=completed_stages,
        last_event_id=last_event_id,
    )


class RecoverPipelineRunUseCase:
    """Find incomplete pipeline runs and replay events to determine resume point.

    Called on application startup to recover from crashes or restarts.
    """

    def __init__(self, event_store: EventStorePort, state_store: StateStorePort) -> None:
        self._event_store = event_store
        self._state_store = state_store

    async def execute(self) -> list[RunStateProjection]:
        """Scan for incomplete runs, replay events, and return recovered projections."""
        incomplete = await self._state_store.list_by_execution_status("running")
        if not incomplete:
            logger.info("No incomplete pipeline runs found for recovery")
            return []
        recovered: list[RunStateProjection] = []
        for projection in incomplete:
            result = await self._recover_single_run(projection.pipeline_run_id)
            recovered.append(result)
        logger.info("Recovered %d incomplete pipeline run(s)", len(recovered))
        return recovered

    async def _recover_single_run(self, pipeline_run_id: str) -> RunStateProjection:
        """Replay events for a single run and persist the recovered projection."""
        events = await self._event_store.get_events_for_run(pipeline_run_id)
        recovered = _build_recovered_projection(pipeline_run_id, events)
        await self._state_store.save_projection(recovered)
        return recovered
