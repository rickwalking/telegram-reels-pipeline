"""AnalyzeTranscriptUseCase — event-sourced wrapper for the transcript analysis stage."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyzeTranscriptCommand:
    """Command value object for triggering transcript analysis."""

    pipeline_run_id: str
    stage_name: str = "transcript"


class AnalyzeTranscriptUseCase:
    """Orchestrate the transcript analysis stage lifecycle via event emission.

    Emits stage_entered before the analysis and stage_completed after.
    The analysis body is a placeholder for the full agent integration.
    """

    def __init__(self, event_emitter: PipelineEventEmitterService) -> None:
        self._event_emitter = event_emitter

    async def execute(self, command: AnalyzeTranscriptCommand) -> None:
        """Run the transcript analysis stage for the given pipeline run.

        Emits stage_entered, performs the analysis (placeholder), then
        emits stage_completed.
        """
        await self._event_emitter.emit_stage_entered(
            pipeline_run_id=command.pipeline_run_id,
            stage_name=command.stage_name,
        )
        logger.info(
            "Transcript analysis stage entered for run %s",
            command.pipeline_run_id,
        )

        # Placeholder: full agent invocation will be wired here
        await self._event_emitter.emit_stage_completed(
            pipeline_run_id=command.pipeline_run_id,
            stage_name=command.stage_name,
        )
        logger.info(
            "Transcript analysis stage completed for run %s",
            command.pipeline_run_id,
        )
