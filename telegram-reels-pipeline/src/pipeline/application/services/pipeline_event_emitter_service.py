"""PipelineEventEmitterService — emits and persists pipeline state events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pipeline.domain.event_types import STAGE_COMPLETED, STAGE_ENTERED
from pipeline.domain.events import PipelineStateEvent

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort


@dataclass(frozen=True)
class StageEventPayload:
    """Payload bundle for a stage lifecycle event emission."""

    pipeline_run_id: str
    stage_name: str
    extra_data: dict[str, Any] | None = None


class PipelineEventEmitterService:
    """Emit stage lifecycle events and persist them via EventStorePort.

    The service is the single authority for constructing PipelineStateEvent
    instances — use cases call emit_stage_entered / emit_stage_completed
    and this service handles timestamping and persistence.
    """

    def __init__(self, event_store: EventStorePort) -> None:
        self._event_store = event_store

    async def emit_stage_entered(self, payload: StageEventPayload) -> None:
        """Emit and persist a stage_entered event for the given stage."""
        event = self._build_event(STAGE_ENTERED, payload)
        await self._event_store.append_event(event)

    async def emit_stage_completed(self, payload: StageEventPayload) -> None:
        """Emit and persist a stage_completed event for the given stage."""
        event = self._build_event(STAGE_COMPLETED, payload)
        await self._event_store.append_event(event)

    def _build_event(
        self, event_type: str, payload: StageEventPayload
    ) -> PipelineStateEvent:
        """Construct an immutable PipelineStateEvent from a StageEventPayload."""
        extra = payload.extra_data or {}
        return PipelineStateEvent(
            event_type=event_type,
            pipeline_run_id=payload.pipeline_run_id,
            stage_name=payload.stage_name,
            timestamp=datetime.now(UTC).isoformat(),
            payload=extra,
        )
