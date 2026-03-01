"""Veo3FireHook — fire Veo3 B-roll generation as a background task after Content stage."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import StageHook
    from pipeline.domain.ports import VideoGenerationPort

logger = logging.getLogger(__name__)


class Veo3FireHook:
    """Fire Veo3 B-roll generation as a background task after Content stage.

    Accepts a ``VideoGenerationPort`` (or ``None`` when no Gemini API key is
    configured).  When the adapter is present and the Content stage has just
    completed, creates a ``Veo3Orchestrator``, fires ``start_generation`` as
    a background ``asyncio.Task``, and stores the task handle in
    ``context.state["veo3_task"]``.

    Failures are logged but never crash the pipeline (graceful degradation).
    """

    if TYPE_CHECKING:
        _protocol_check: StageHook

    def __init__(self, veo3_adapter: VideoGenerationPort | None) -> None:
        self._veo3_adapter = veo3_adapter

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        """Return True only for Content + post when an adapter is available."""
        return stage == PipelineStage.CONTENT and phase == "post" and self._veo3_adapter is not None

    async def execute(self, context: PipelineContext) -> None:
        """Create a Veo3Orchestrator and fire background generation.

        Stores the ``asyncio.Task`` in ``context.state["veo3_task"]``.
        On any failure, logs the error and returns without crashing.
        """
        if self._veo3_adapter is None:
            return

        workspace = context.require_workspace()

        try:
            from pipeline.application.veo3_orchestrator import Veo3Orchestrator

            orchestrator = Veo3Orchestrator(
                video_gen=self._veo3_adapter,
                clip_count=context.settings.veo3_clip_count,
                timeout_s=context.settings.veo3_timeout_s,
            )
            run_id = workspace.name
            task: asyncio.Task[None] = asyncio.create_task(
                orchestrator.start_generation(workspace, run_id),
                name=f"veo3-gen-{run_id}",
            )
            context.state.veo3_task = task
            logger.info("Veo3 background generation fired for run %s", run_id)
            print("  [VEO3] Background generation started")
        except Exception:
            logger.warning("Veo3 generation fire failed — continuing pipeline", exc_info=True)
            print("  [VEO3] Generation fire failed — continuing without B-roll")
