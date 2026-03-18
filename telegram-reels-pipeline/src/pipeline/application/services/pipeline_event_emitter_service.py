"""PipelineEventEmitterService — thin wrapper that stamps and publishes pipeline events."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.domain import event_types
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent

if TYPE_CHECKING:
    from pipeline.application.event_bus import EventBus


class PipelineEventEmitterService:
    """Stamp, construct, and publish typed pipeline events via the EventBus.

    Encapsulates timestamp generation and MappingProxyType construction so
    callers only supply business-relevant fields.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus

    async def emit_stage_entered(self, pipeline_run_id: str, stage: PipelineStage) -> None:
        """Publish a stage_entered event for the given run and stage."""
        await self._event_bus.publish(
            PipelineEvent(
                timestamp=self._utc_now(),
                event_name=event_types.STAGE_ENTERED,
                stage=stage,
                data={"pipeline_run_id": pipeline_run_id},
            )
        )

    async def emit_stage_completed(
        self,
        pipeline_run_id: str,
        stage: PipelineStage,
        artifact_paths: tuple[str, ...],
    ) -> None:
        """Publish a stage_completed event with the produced artifact paths."""
        await self._event_bus.publish(
            PipelineEvent(
                timestamp=self._utc_now(),
                event_name=event_types.STAGE_COMPLETED,
                stage=stage,
                data={
                    "pipeline_run_id": pipeline_run_id,
                    "artifact_paths": artifact_paths,
                },
            )
        )

    @staticmethod
    def _utc_now() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return datetime.now(UTC).isoformat()
