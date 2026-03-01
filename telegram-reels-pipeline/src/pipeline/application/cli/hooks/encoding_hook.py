"""EncodingPlanHook — execute FFmpeg encoding plan after FFmpeg Engineer stage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import StageHook
    from pipeline.infrastructure.adapters.ffmpeg_adapter import FFmpegAdapter

logger = logging.getLogger(__name__)


class EncodingPlanHook:
    """Execute FFmpeg encoding plan after FFmpeg Engineer stage.

    Reads ``encoding-plan.json`` from the workspace, executes each
    segment command via the FFmpeg adapter, prints progress, and
    re-collects artifacts so downstream stages see the produced segments.

    Raises ``RuntimeError`` if the encoding plan file is missing (the
    FFmpeg Engineer stage should always produce it).
    """

    if TYPE_CHECKING:
        _protocol_check: StageHook

    def __init__(self, ffmpeg_adapter: FFmpegAdapter) -> None:
        self._ffmpeg_adapter = ffmpeg_adapter

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        """Return True only for FFMPEG_ENGINEER + post."""
        return stage == PipelineStage.FFMPEG_ENGINEER and phase == "post"

    async def execute(self, context: PipelineContext) -> None:
        """Execute the encoding plan and re-collect workspace artifacts.

        Reads ``encoding-plan.json``, runs FFmpeg commands for each segment
        via the adapter, and updates ``context.artifacts`` with the new
        workspace file listing.
        """
        workspace = context.require_workspace()
        plan_path = workspace / "encoding-plan.json"

        if not plan_path.exists():
            raise RuntimeError("FFmpeg Engineer completed but encoding-plan.json is missing")

        print("  [FFMPEG_ADAPTER] Executing encoding plan...")
        segments = await self._ffmpeg_adapter.execute_encoding_plan(plan_path, workspace=workspace)
        print(f"  [FFMPEG_ADAPTER] Produced {len(segments)} segments")
        for seg in segments:
            print(f"      - {seg.name}")

        # Re-collect artifacts so downstream stages see the segment files
        from pipeline.infrastructure.adapters.artifact_collector import collect_artifacts

        context.artifacts = collect_artifacts(workspace)
