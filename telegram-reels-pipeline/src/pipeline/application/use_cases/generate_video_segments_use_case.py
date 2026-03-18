"""GenerateVideoSegmentsUseCase — event-sourced wrapper for FFmpeg segment generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService


@dataclass(frozen=True)
class GenerateSegmentsCommand:
    """Command value object for the generate-video-segments use case.

    Carries the pipeline run identifier and the stage name to emit
    into the event stream.
    """

    pipeline_run_id: str
    stage_name: str = "ffmpeg_engineer"

    def __post_init__(self) -> None:
        """Validate that the run identifier is non-empty."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")


class GenerateVideoSegmentsUseCase:
    """Orchestrate FFmpeg segment generation with event-sourced observability.

    Emits ``stage_entered`` before execution and ``stage_completed`` — with
    the produced segment artifact paths — on success.
    """

    PLACEHOLDER_SEGMENT_PATHS: tuple[str, ...] = (
        "segment-001.mp4",
        "segment-002.mp4",
    )

    def __init__(self, event_emitter: PipelineEventEmitterService) -> None:
        self._event_emitter = event_emitter

    async def execute(self, command: GenerateSegmentsCommand) -> None:
        """Execute the FFmpeg segment generation stage for the given run.

        Emits stage_entered, performs (placeholder) FFmpeg execution, then
        emits stage_completed with the resulting segment paths.
        """
        stage = PipelineStage.FFMPEG_ENGINEER
        await self._event_emitter.emit_stage_entered(command.pipeline_run_id, stage)
        segment_paths = await self._run_ffmpeg_placeholder(command.pipeline_run_id)
        await self._event_emitter.emit_stage_completed(
            command.pipeline_run_id,
            stage,
            segment_paths,
        )

    async def _run_ffmpeg_placeholder(self, pipeline_run_id: str) -> tuple[str, ...]:
        """Placeholder FFmpeg execution — returns deterministic segment paths.

        This will be replaced by the real FFmpeg adapter call once the
        infrastructure layer is wired at the Composition Root.
        """
        return tuple(
            f"{pipeline_run_id}/{path}" for path in self.PLACEHOLDER_SEGMENT_PATHS
        )
