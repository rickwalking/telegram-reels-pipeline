"""PipelineEventEmitterService — high-level event emission for pipeline lifecycle."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.event_types import (
    ERROR_OCCURRED,
    PIPELINE_PAUSED,
    PIPELINE_RESUMED,
    QA_GATE_FAILED,
    QA_GATE_PASSED,
    QA_GATE_REWORK,
    STAGE_COMPLETED,
    STAGE_ENTERED,
)
from pipeline.domain.events import PipelineStateEvent, RunStateProjection

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort
    from pipeline.domain.ports.state_store_port import StateStorePort

_QA_DECISION_TO_EVENT_TYPE: Mapping[str, str] = MappingProxyType(
    {
        "PASS": QA_GATE_PASSED,
        "REWORK": QA_GATE_REWORK,
        "FAIL": QA_GATE_FAILED,
    }
)


@dataclass(frozen=True)
class StageEventPayload:
    """Parameters for stage lifecycle events."""

    pipeline_run_id: str
    stage_name: str
    artifact_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class QaEventPayload:
    """Parameters for QA gate events."""

    pipeline_run_id: str
    stage_name: str
    qa_decision: str
    critique_payload: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True)
class ErrorEventPayload:
    """Parameters for error events."""

    pipeline_run_id: str
    stage_name: str
    error_message: str


def _build_event(event_type: str, pipeline_run_id: str, stage_name: str) -> PipelineStateEvent:
    """Build a PipelineStateEvent with generated ID and current timestamp."""
    return PipelineStateEvent(
        event_id=uuid.uuid4().hex,
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        timestamp=datetime.now(tz=UTC).isoformat(),
        stage_name=stage_name,
    )


def _build_event_with_payload(
    event_type: str,
    pipeline_run_id: str,
    stage_name: str,
    payload: Mapping[str, object],
) -> PipelineStateEvent:
    """Build a PipelineStateEvent with extra payload data."""
    return PipelineStateEvent(
        event_id=uuid.uuid4().hex,
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        timestamp=datetime.now(tz=UTC).isoformat(),
        stage_name=stage_name,
        payload=payload,
    )


class PipelineEventEmitterService:
    """Wraps EventStorePort + StateStorePort for high-level event emission.

    Each emit method builds an event, appends it to the store, and updates
    the materialized projection.
    """

    def __init__(self, event_store: EventStorePort, state_store: StateStorePort) -> None:
        self._event_store = event_store
        self._state_store = state_store

    async def emit_stage_entered(self, payload: StageEventPayload) -> None:
        """Emit STAGE_ENTERED event and update projection to the entered stage."""
        event = _build_event(STAGE_ENTERED, payload.pipeline_run_id, payload.stage_name)
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=payload.stage_name,
            execution_status=projection.execution_status,
            stages_completed=projection.stages_completed,
            last_event_id=event.event_id,
        )
        await self._state_store.save_projection(updated)

    async def emit_stage_completed(self, payload: StageEventPayload) -> None:
        """Emit STAGE_COMPLETED event with artifact paths and update projection."""
        event_payload: Mapping[str, object] = MappingProxyType({"artifact_paths": payload.artifact_paths})
        event = _build_event_with_payload(STAGE_COMPLETED, payload.pipeline_run_id, payload.stage_name, event_payload)
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        completed = projection.stages_completed + (payload.stage_name,)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=payload.stage_name,
            execution_status=projection.execution_status,
            stages_completed=completed,
            last_event_id=event.event_id,
        )
        await self._state_store.save_projection(updated)

    async def emit_qa_gate_result(self, payload: QaEventPayload) -> None:
        """Emit QA gate event dispatched from qa_decision string."""
        event_type = _QA_DECISION_TO_EVENT_TYPE.get(payload.qa_decision)
        if event_type is None:
            raise ValueError(f"Unknown qa_decision: {payload.qa_decision}")
        event = _build_event_with_payload(
            event_type, payload.pipeline_run_id, payload.stage_name, payload.critique_payload
        )
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=projection.current_stage,
            execution_status=projection.execution_status,
            stages_completed=projection.stages_completed,
            last_event_id=event.event_id,
        )
        await self._state_store.save_projection(updated)

    async def emit_error_occurred(self, payload: ErrorEventPayload) -> None:
        """Emit ERROR_OCCURRED event and mark projection as failed."""
        event_payload: Mapping[str, object] = MappingProxyType({"error_message": payload.error_message})
        event = _build_event_with_payload(ERROR_OCCURRED, payload.pipeline_run_id, payload.stage_name, event_payload)
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=projection.current_stage,
            execution_status="failed",
            stages_completed=projection.stages_completed,
            last_event_id=event.event_id,
            error_message=payload.error_message,
        )
        await self._state_store.save_projection(updated)

    async def emit_pipeline_paused(self, payload: StageEventPayload) -> None:
        """Emit PIPELINE_PAUSED event and mark projection as paused."""
        event = _build_event(PIPELINE_PAUSED, payload.pipeline_run_id, payload.stage_name)
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=projection.current_stage,
            execution_status="paused",
            stages_completed=projection.stages_completed,
            last_event_id=event.event_id,
        )
        await self._state_store.save_projection(updated)

    async def emit_pipeline_resumed(self, payload: StageEventPayload) -> None:
        """Emit PIPELINE_RESUMED event and mark projection as running."""
        event = _build_event(PIPELINE_RESUMED, payload.pipeline_run_id, payload.stage_name)
        await self._event_store.append_event(event)
        projection = await self._load_or_create_projection(payload.pipeline_run_id, payload.stage_name)
        updated = RunStateProjection(
            pipeline_run_id=projection.pipeline_run_id,
            current_stage=projection.current_stage,
            execution_status="running",
            stages_completed=projection.stages_completed,
            last_event_id=event.event_id,
        )
        await self._state_store.save_projection(updated)

    async def _load_or_create_projection(self, pipeline_run_id: str, stage_name: str) -> RunStateProjection:
        """Load existing projection or create a default one."""
        existing = await self._state_store.load_projection(pipeline_run_id)
        if existing is not None:
            return existing
        return RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            current_stage=stage_name,
            execution_status="running",
        )
