"""DetectCameraLayoutUseCase — event-sourced wrapper for the layout_detective stage."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService

logger = logging.getLogger(__name__)

UNKNOWN_LAYOUT_NAME: str = "unknown"


@dataclass(frozen=True)
class DetectLayoutCommand:
    """Command to trigger camera layout detection for a pipeline run."""

    pipeline_run_id: str
    stage_name: str = field(default="layout_detective")

    def __post_init__(self) -> None:
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.stage_name:
            raise ValueError("stage_name must not be empty")


class DetectCameraLayoutUseCase:
    """Orchestrate camera layout detection as an event-sourced pipeline stage.

    Emits stage_entered and stage_completed events on success.
    Emits escalation_requested when the detected layout is unknown.
    """

    def __init__(self, event_emitter: PipelineEventEmitterService) -> None:
        self._event_emitter = event_emitter

    async def execute(self, command: DetectLayoutCommand) -> None:
        """Run layout detection and emit lifecycle events.

        Emits stage_entered, then either stage_completed or escalation_requested.
        Placeholder: layout is treated as unknown until Stage 5 agent is wired in.
        """
        stage = PipelineStage.LAYOUT_DETECTIVE
        pipeline_run_id = command.pipeline_run_id

        await self._event_emitter.emit_stage_entered(stage, pipeline_run_id)
        logger.info("Layout detection started for run %s", pipeline_run_id)

        detected_layout_name = self._detect_layout_placeholder()

        if detected_layout_name == UNKNOWN_LAYOUT_NAME:
            await self._handle_unknown_layout(stage, pipeline_run_id)
            return

        await self._event_emitter.emit_stage_completed(stage, pipeline_run_id)
        logger.info("Layout detection completed for run %s: %s", pipeline_run_id, detected_layout_name)

    async def _handle_unknown_layout(self, stage: PipelineStage, pipeline_run_id: str) -> None:
        """Emit escalation event when layout cannot be determined."""
        logger.warning("Unknown layout detected for run %s — escalating", pipeline_run_id)
        await self._event_emitter.emit_escalation_requested(stage, pipeline_run_id)

    def _detect_layout_placeholder(self) -> str:
        """Placeholder returning unknown until Stage 5 agent integration is complete."""
        return UNKNOWN_LAYOUT_NAME
