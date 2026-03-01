"""RunStageCommand — run a single pipeline stage with pre/post hooks."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.application.cli.stage_registry import ALL_STAGES, TOTAL_CLI_STAGES, stage_name
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest, ReflectionResult

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult, OutputPort, StageHook
    from pipeline.application.stage_runner import StageRunner

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["ALL_STAGES", "TOTAL_CLI_STAGES", "stage_name", "RunStageCommand"]


def print_stage_result(
    stage: PipelineStage,
    result: ReflectionResult,
    artifacts: tuple[Path, ...],
    elapsed: float,
    output: OutputPort = print,
) -> None:
    """Print stage completion summary."""
    output(f"  [{stage.value.upper()}] Done in {elapsed:.1f}s")
    output(f"    Decision: {result.best_critique.decision.value}")
    output(f"    Score: {result.best_critique.score}")
    output(f"    Attempts: {result.attempts}")
    output(f"    Artifacts: {len(artifacts)}")
    for a in artifacts:
        output(f"      - {a.name}")


def _build_elicitation_context(state: object) -> dict[str, str]:
    """Build elicitation context dict, merging in creative instructions."""
    from pipeline.application.cli.context import PipelineState

    if not isinstance(state, PipelineState):
        return {}
    result = dict(state.elicitation)
    if state.instructions:
        result["instructions"] = state.instructions
    return result


async def _run_hooks(
    hooks: tuple[StageHook, ...],
    stage: PipelineStage,
    phase: str,
    context: PipelineContext,
) -> None:
    """Fire all hooks matching the given stage and phase."""
    for hook in hooks:
        if hook.should_run(stage, phase):
            await hook.execute(context)


def _build_result_data(
    stage_num: int,
    stage: PipelineStage,
    result: ReflectionResult,
    elapsed: float,
) -> dict[str, object]:
    """Build the CommandResult data dict for a completed stage."""
    return {
        "stage_num": stage_num,
        "stage": stage.value,
        "escalation_needed": result.escalation_needed,
        "attempts": result.attempts,
        "score": result.best_critique.score,
        "elapsed": elapsed,
    }


class RunStageCommand:
    """Run a single pipeline stage with pre/post hooks."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(
        self,
        stage_runner: StageRunner,
        hooks: tuple[StageHook, ...] = (),
        output: OutputPort = print,
    ) -> None:
        self._stage_runner = stage_runner
        self._hooks = hooks
        self._output = output

    @property
    def name(self) -> str:
        return "run-stage"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Execute a single pipeline stage with hook support."""
        from types import MappingProxyType

        from pipeline.application.cli.protocols import CommandResult
        from pipeline.domain.types import GateName

        stage_num: int = context.state.current_stage_num
        stage_spec = context.state.stage_spec
        if stage_spec is None:
            return CommandResult(success=False, message="No stage_spec in context state")
        stage, step_file_name, agent_def_name, gate_name = stage_spec
        step_file = context.project_root / "workflows" / "stages" / step_file_name
        agent_def = context.project_root / "agents" / agent_def_name / "agent.md"
        gate_criteria: str = context.state.gate_criteria
        elicitation = _build_elicitation_context(context.state)

        self._output(f"  [{stage.value.upper()}] Starting...")
        stage_start = time.monotonic()

        await _run_hooks(self._hooks, stage, "pre", context)

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

            print_stage_result(stage, result, context.artifacts, elapsed, output=self._output)
            await _run_hooks(self._hooks, stage, "post", context)

            success = not result.escalation_needed
            msg = f"Stage {stage_num} ({stage.value}) {'completed' if success else 'escalated'}"
            return CommandResult(
                success=success,
                message=msg,
                data=_build_result_data(stage_num, stage, result, elapsed),
            )

        except Exception:
            elapsed = time.monotonic() - stage_start
            self._output(f"  [{stage.value.upper()}] FAILED after {elapsed:.1f}s")
            await _run_hooks(self._hooks, stage, "post", context)
            raise
