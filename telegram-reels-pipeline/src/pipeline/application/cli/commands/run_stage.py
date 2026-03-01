"""RunStageCommand — run a single pipeline stage with pre/post hooks."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest, ReflectionResult

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult, StageHook
    from pipeline.application.stage_runner import StageRunner

logger = logging.getLogger(__name__)

# All pipeline stages in order (delivery skipped — no Telegram)
ALL_STAGES = (
    (PipelineStage.ROUTER, "stage-01-router.md", "router", "router"),
    (PipelineStage.RESEARCH, "stage-02-research.md", "research", "research"),
    (PipelineStage.TRANSCRIPT, "stage-03-transcript.md", "transcript", "transcript"),
    (PipelineStage.CONTENT, "stage-04-content.md", "content-creator", "content"),
    (PipelineStage.LAYOUT_DETECTIVE, "stage-05-layout-detective.md", "layout-detective", "layout"),
    (PipelineStage.FFMPEG_ENGINEER, "stage-06-ffmpeg-engineer.md", "ffmpeg-engineer", "ffmpeg"),
    (PipelineStage.ASSEMBLY, "stage-07-assembly.md", "qa", "assembly"),
)

TOTAL_CLI_STAGES: int = len(ALL_STAGES)


def stage_name(stage_num: int) -> str:
    """Return the human-readable display name for a 1-indexed stage number."""
    if 1 <= stage_num <= TOTAL_CLI_STAGES:
        return ALL_STAGES[stage_num - 1][0].value.replace("_", "-")
    return f"stage-{stage_num}"


def print_stage_result(
    stage: PipelineStage,
    result: ReflectionResult,
    artifacts: tuple[Path, ...],
    elapsed: float,
) -> None:
    """Print stage completion summary."""
    print(f"  [{stage.value.upper()}] Done in {elapsed:.1f}s")
    print(f"    Decision: {result.best_critique.decision.value}")
    print(f"    Score: {result.best_critique.score}")
    print(f"    Attempts: {result.attempts}")
    print(f"    Artifacts: {len(artifacts)}")
    for a in artifacts:
        print(f"      - {a.name}")


class RunStageCommand:
    """Run a single pipeline stage with pre/post hooks."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(self, stage_runner: StageRunner, hooks: tuple[StageHook, ...] = ()) -> None:
        self._stage_runner = stage_runner
        self._hooks = hooks

    @property
    def name(self) -> str:
        return "run-stage"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Execute a single pipeline stage with hook support.

        Reads from context:
            - ``state["current_stage_num"]``: 1-indexed stage number
            - ``state["stage_spec"]``: Tuple of (PipelineStage, step_file, agent_def, gate_name)
            - ``state["gate_criteria"]``: Gate criteria text
            - ``state["elicitation"]``: Elicitation context dict

        Fires pre-hooks before stage execution and post-hooks after
        (even on failure). Updates ``context.artifacts`` on success.

        Returns:
            CommandResult with stage result data.
        """
        from types import MappingProxyType

        from pipeline.application.cli.protocols import CommandResult
        from pipeline.domain.types import GateName

        stage_num: int = context.state["current_stage_num"]
        stage_spec: tuple[PipelineStage, Path, Path, str] = context.state["stage_spec"]
        stage, step_file, agent_def, gate_name = stage_spec
        gate_criteria: str = context.state.get("gate_criteria", "")
        elicitation: dict[str, str] = context.state.get("elicitation", {})

        # Forward creative instructions to elicitation context if present
        instructions = context.state.get("instructions", "")
        if instructions:
            elicitation["instructions"] = instructions

        print(f"  [{stage.value.upper()}] Starting...")
        stage_start = time.monotonic()

        # Fire pre-hooks
        for hook in self._hooks:
            if hook.should_run(stage, "pre"):
                await hook.execute(context)

        try:
            request = AgentRequest(
                stage=stage,
                step_file=step_file,
                agent_definition=agent_def,
                prior_artifacts=context.artifacts,
                elicitation_context=MappingProxyType(elicitation),
            )
            result = await self._stage_runner.run_stage(
                request,
                gate=GateName(gate_name),
                gate_criteria=gate_criteria,
            )
            context.artifacts = result.artifacts

            elapsed = time.monotonic() - stage_start
            print_stage_result(stage, result, context.artifacts, elapsed)

            # Fire post-hooks
            for hook in self._hooks:
                if hook.should_run(stage, "post"):
                    await hook.execute(context)

            if result.escalation_needed:
                return CommandResult(
                    success=False,
                    message=f"Stage {stage_num} ({stage.value}) escalated",
                    data={
                        "stage_num": stage_num,
                        "stage": stage.value,
                        "escalation_needed": True,
                        "attempts": result.attempts,
                        "score": result.best_critique.score,
                        "elapsed": elapsed,
                    },
                )

            return CommandResult(
                success=True,
                message=f"Stage {stage_num} ({stage.value}) completed",
                data={
                    "stage_num": stage_num,
                    "stage": stage.value,
                    "escalation_needed": False,
                    "attempts": result.attempts,
                    "score": result.best_critique.score,
                    "elapsed": elapsed,
                },
            )

        except Exception:
            elapsed = time.monotonic() - stage_start
            print(f"  [{stage.value.upper()}] FAILED after {elapsed:.1f}s")

            # Fire post-hooks even on failure
            for hook in self._hooks:
                if hook.should_run(stage, "post"):
                    await hook.execute(context)

            raise
