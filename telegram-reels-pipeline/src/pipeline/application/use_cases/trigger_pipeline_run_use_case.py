"""Application use case: trigger a new pipeline run from an external command."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus, RunExecutionStatus
from pipeline.domain.event_types import PIPELINE_RUN_CREATED
from pipeline.domain.events import CreatePipelineRunCommand, PipelineStateEvent, RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.ports import EventStorePort, ProjectionStorePort


class TriggerPipelineRunUseCase:
    """Create a new pipeline run from an incoming trigger command."""

    def __init__(
        self,
        event_store_port: EventStorePort,
        projection_store_port: ProjectionStorePort,
    ) -> None:
        self._event_store_port = event_store_port
        self._projection_store_port = projection_store_port

    async def execute(self, command: CreatePipelineRunCommand) -> RunStateProjection:
        """Persist the creation event and build the initial state projection."""
        pipeline_run_id = _generate_pipeline_run_id()
        now_iso = datetime.now(UTC).isoformat()

        event = _build_creation_event(pipeline_run_id, command, now_iso)
        await self._event_store_port.append_event(event)

        projection = _build_initial_projection(pipeline_run_id, command, now_iso)
        await self._projection_store_port.save_projection(projection)
        return projection


def _generate_pipeline_run_id() -> str:
    """Build a time-prefixed unique identifier for a pipeline run."""
    timestamp_prefix = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{timestamp_prefix}-{short_uuid}"


def _build_creation_event(
    pipeline_run_id: str,
    command: CreatePipelineRunCommand,
    now_iso: str,
) -> PipelineStateEvent:
    """Construct the PIPELINE_RUN_CREATED event from the trigger command."""
    return PipelineStateEvent(
        event_id=f"evt-{uuid.uuid4().hex[:12]}",
        pipeline_run_id=pipeline_run_id,
        event_type=PIPELINE_RUN_CREATED,
        stage_name=PipelineStage.ROUTER.value,
        payload_data=MappingProxyType({
            "youtube_url": command.youtube_url,
            "topic_focus": command.topic_focus,
            "trigger_source": command.trigger_source,
        }),
        created_at=now_iso,
    )


def _build_initial_projection(
    pipeline_run_id: str,
    command: CreatePipelineRunCommand,
    now_iso: str,
) -> RunStateProjection:
    """Construct the initial materialized state projection for a new run."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url=command.youtube_url,
        trigger_source=command.trigger_source,
        current_stage=PipelineStage.ROUTER.value,
        execution_status=RunExecutionStatus.PENDING.value,
        current_attempt_count=0,
        qa_evaluation_status=QAStatus.PENDING.value,
        completed_stages=(),
        escalation_status=EscalationState.NONE.value,
        created_at=now_iso,
        last_updated_at=now_iso,
    )
