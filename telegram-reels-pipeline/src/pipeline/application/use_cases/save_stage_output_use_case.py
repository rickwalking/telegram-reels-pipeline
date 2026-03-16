"""Application use case: save the output of a completed pipeline stage as an event."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.event_types import STAGE_OUTPUT_SAVED
from pipeline.domain.events import PipelineStateEvent, RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort
    from pipeline.domain.ports.state_store_port import StateStorePort


@dataclass(frozen=True)
class SaveStageOutputCommand:
    """Command carrying the data needed to persist one stage's output."""

    pipeline_run_id: str
    stage_name: str
    payload_data: Mapping[str, object]


class SaveStageOutputUseCase:
    """Persist a stage output event and update the run's completed_stages projection."""

    def __init__(
        self,
        event_store_port: EventStorePort,
        state_store_port: StateStorePort,
    ) -> None:
        self._event_store_port = event_store_port
        self._state_store_port = state_store_port

    async def execute(self, command: SaveStageOutputCommand) -> str:
        """Save stage output as an event and update the projection.

        Returns the event_id of the saved event.
        """
        now_iso = datetime.now(UTC).isoformat()
        event = _build_stage_output_event(command, now_iso)
        await self._event_store_port.append_event(event)

        projection = await self._state_store_port.load_projection(command.pipeline_run_id)
        if projection is not None:
            updated_projection = _append_completed_stage(projection, command, now_iso)
            await self._state_store_port.save_state(updated_projection)
        return event.event_id


def _build_stage_output_event(
    command: SaveStageOutputCommand,
    now_iso: str,
) -> PipelineStateEvent:
    """Construct a STAGE_OUTPUT_SAVED event from the save command."""
    return PipelineStateEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        pipeline_run_id=command.pipeline_run_id,
        event_type=STAGE_OUTPUT_SAVED,
        stage_name=command.stage_name,
        payload_data=MappingProxyType(dict(command.payload_data)),
        created_at=now_iso,
    )


def _append_completed_stage(
    projection: RunStateProjection,
    command: SaveStageOutputCommand,
    now_iso: str,
) -> RunStateProjection:
    """Return a projection with the stage name appended to completed_stages."""
    already_completed = projection.completed_stages
    stage_is_new = command.stage_name not in already_completed
    new_completed = (*already_completed, command.stage_name) if stage_is_new else already_completed
    return RunStateProjection(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=projection.execution_status,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=new_completed,
        escalation_status=projection.escalation_status,
        created_at=projection.created_at,
        last_updated_at=now_iso,
    )
