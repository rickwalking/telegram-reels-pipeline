"""DownloadVideoUseCase — event-sourced wrapper for video download stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.application.services.pipeline_event_emitter_service import (
    StageEventPayload,
)

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import (
        PipelineEventEmitterService,
    )

# Stage name matches the research stage where download happens in the pipeline
DOWNLOAD_STAGE_NAME: str = "research"

# Placeholder artifact paths emitted until real yt-dlp wiring is added
_PLACEHOLDER_VIDEO_FILE_PATH: str = ""
_PLACEHOLDER_AUDIO_FILE_PATH: str = ""
_PLACEHOLDER_SUBTITLE_FILE_PATH: str = ""


class DownloadVideoUseCase:
    """Orchestrate the video download stage with event-sourced observability.

    Emits stage_entered before the download and stage_completed after,
    so the event store tracks progress in real time.
    The actual yt-dlp call is a placeholder to be wired in a later story.
    """

    def __init__(self, event_emitter: PipelineEventEmitterService) -> None:
        self._event_emitter = event_emitter

    async def execute(self, pipeline_run_id: str, youtube_url: str) -> None:
        """Run the download stage, emitting lifecycle events.

        Args:
            pipeline_run_id: Unique identifier for the pipeline run.
            youtube_url: The YouTube URL to download.
        """
        await self._emit_stage_entered(pipeline_run_id)
        artifact_paths = self._build_placeholder_artifact_paths(youtube_url)
        await self._emit_stage_completed(pipeline_run_id, artifact_paths)

    async def _emit_stage_entered(self, pipeline_run_id: str) -> None:
        """Emit the stage_entered lifecycle event."""
        payload = StageEventPayload(
            pipeline_run_id=pipeline_run_id,
            stage_name=DOWNLOAD_STAGE_NAME,
        )
        await self._event_emitter.emit_stage_entered(payload)

    async def _emit_stage_completed(
        self, pipeline_run_id: str, artifact_paths: dict[str, str]
    ) -> None:
        """Emit the stage_completed lifecycle event with artifact paths."""
        payload = StageEventPayload(
            pipeline_run_id=pipeline_run_id,
            stage_name=DOWNLOAD_STAGE_NAME,
            extra_data=artifact_paths,
        )
        await self._event_emitter.emit_stage_completed(payload)

    def _build_placeholder_artifact_paths(self, youtube_url: str) -> dict[str, str]:
        """Build placeholder artifact path dict until real download is wired."""
        return {
            "youtube_url": youtube_url,
            "video_file_path": _PLACEHOLDER_VIDEO_FILE_PATH,
            "audio_file_path": _PLACEHOLDER_AUDIO_FILE_PATH,
            "subtitle_file_path": _PLACEHOLDER_SUBTITLE_FILE_PATH,
        }
