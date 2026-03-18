"""PipelineEventEmitterService — wraps EventBus with typed stage lifecycle helpers."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.domain import event_types
from pipeline.domain.models import PipelineEvent

if TYPE_CHECKING:
    from pipeline.application.event_bus import EventBus

logger = logging.getLogger(__name__)


class PipelineEventEmitterService:
    """Publish typed pipeline lifecycle events via the EventBus.

    Provides semantic helpers so callers never hand-craft event_name strings.
    All timestamps are generated at call time in UTC ISO-8601 format.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    async def emit_stage_entered(self, pipeline_run_id: str, stage_name: str) -> None:
        """Emit a stage_entered event for the given stage."""
        event = PipelineEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_name=event_types.STAGE_ENTERED,
            data={"pipeline_run_id": pipeline_run_id, "stage_name": stage_name},
        )
        await self._event_bus.publish(event)
        logger.debug("Emitted %s for stage %s", event_types.STAGE_ENTERED, stage_name)

    async def emit_stage_completed(self, pipeline_run_id: str, stage_name: str) -> None:
        """Emit a stage_completed event for the given stage."""
        event = PipelineEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_name=event_types.STAGE_COMPLETED,
            data={"pipeline_run_id": pipeline_run_id, "stage_name": stage_name},
        )
        await self._event_bus.publish(event)
        logger.debug("Emitted %s for stage %s", event_types.STAGE_COMPLETED, stage_name)

    async def emit_stage_failed(self, pipeline_run_id: str, stage_name: str, reason: str) -> None:
        """Emit a stage_failed event for the given stage."""
        event = PipelineEvent(
            timestamp=datetime.now(UTC).isoformat(),
            event_name=event_types.STAGE_FAILED,
            data={"pipeline_run_id": pipeline_run_id, "stage_name": stage_name, "reason": reason},
        )
        await self._event_bus.publish(event)
        logger.debug("Emitted %s for stage %s", event_types.STAGE_FAILED, stage_name)
