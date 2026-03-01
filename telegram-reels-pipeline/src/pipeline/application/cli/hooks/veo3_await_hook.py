"""Veo3AwaitHook — await Veo3 B-roll completion before Assembly stage."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Literal

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.app.settings import PipelineSettings
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import StageHook
    from pipeline.domain.ports import VideoGenerationPort

logger = logging.getLogger(__name__)


class Veo3AwaitHook:
    """Await Veo3 B-roll completion before Assembly stage.

    Runs as a pre-Assembly hook.  First awaits the background generation
    task (if one was stored by ``Veo3FireHook``), then runs the Veo3 await
    gate to poll for final results.

    Failures are logged but never crash the pipeline (graceful degradation).
    """

    if TYPE_CHECKING:
        _protocol_check: StageHook

    def __init__(
        self,
        veo3_adapter: VideoGenerationPort | None,
        settings: PipelineSettings,
    ) -> None:
        self._veo3_adapter = veo3_adapter
        self._settings = settings

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        """Return True only for Assembly + pre."""
        return stage == PipelineStage.ASSEMBLY and phase == "pre"

    async def execute(self, context: PipelineContext) -> None:
        """Await background Veo3 task and run the polling gate.

        Reads ``context.state["veo3_task"]`` if present, awaits it, then
        creates a fresh orchestrator to run the await gate.  Prints a
        summary of completed / failed / skipped clips.
        """
        from pipeline.application.veo3_await_gate import run_veo3_await_gate
        from pipeline.application.veo3_orchestrator import Veo3Orchestrator

        workspace = context.require_workspace()

        print("  [VEO3] Awaiting generation completion...")
        try:
            veo3_task: asyncio.Task[None] | None = context.state.get("veo3_task")
            if veo3_task is not None:
                try:
                    await veo3_task
                except Exception:
                    logger.warning("Veo3 background task failed", exc_info=True)
                    print("  [VEO3] Background task failed — checking partial results")

            orchestrator: Veo3Orchestrator | None = None
            if self._veo3_adapter is not None:
                orchestrator = Veo3Orchestrator(
                    video_gen=self._veo3_adapter,
                    clip_count=self._settings.veo3_clip_count,
                    timeout_s=self._settings.veo3_timeout_s,
                )

            summary = await run_veo3_await_gate(
                workspace=workspace,
                orchestrator=orchestrator,
                timeout_s=self._settings.veo3_timeout_s,
            )
            logger.info("Veo3 await gate result: %s", summary)
            if summary.get("skipped"):
                print(f"  [VEO3] Skipped — {summary.get('reason', 'no jobs')}")
            else:
                completed = summary.get("completed", 0)
                failed = summary.get("failed", 0)
                total = summary.get("total", 0)
                print(f"  [VEO3] Gate done — {completed}/{total} completed, {failed} failed")
        except Exception:
            logger.warning("Veo3 await gate failed — continuing pipeline", exc_info=True)
            print("  [VEO3] Await gate failed — continuing without B-roll")
