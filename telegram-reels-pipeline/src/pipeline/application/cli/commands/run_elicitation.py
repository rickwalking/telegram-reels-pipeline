"""RunElicitationCommand — run router stage with interactive elicitation loop."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest, ReflectionResult
from pipeline.domain.types import GateName

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult, InputReader
    from pipeline.application.stage_runner import StageRunner

logger = logging.getLogger(__name__)

MAX_ELICITATION_ROUNDS: int = 2
MAX_QUESTIONS_PER_ROUND: int = 5
MTIME_TOLERANCE_SECONDS: float = 2.0


def is_interactive() -> bool:
    """Check if stdin is an interactive terminal (TTY)."""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def find_router_output(
    artifacts: tuple[Path, ...],
    workspace: Path,
    min_mtime: float = 0.0,
) -> Path | None:
    """Find router-output.json, preferring stage result artifacts over workspace-global.

    Args:
        artifacts: Stage result artifact paths (checked first).
        workspace: Workspace directory (fallback).
        min_mtime: Minimum file mtime (epoch). Files older than this are skipped
                   to avoid reading stale output from previous runs.
    """
    adjusted_mtime = min_mtime - MTIME_TOLERANCE_SECONDS if min_mtime else 0.0
    for artifact in artifacts:
        if artifact.name == "router-output.json":
            try:
                mtime = artifact.stat().st_mtime
            except FileNotFoundError:
                continue
            if adjusted_mtime and mtime < adjusted_mtime:
                continue
            return artifact
    fallback = workspace / "router-output.json"
    try:
        mtime = fallback.stat().st_mtime
    except FileNotFoundError:
        return None
    if adjusted_mtime and mtime < adjusted_mtime:
        logger.debug("Skipping stale workspace router-output.json (mtime < stage start)")
        return None
    return fallback


def parse_router_output(
    artifacts: tuple[Path, ...],
    workspace: Path,
    min_mtime: float = 0.0,
) -> dict[str, object] | None:
    """Parse router-output.json from artifacts or workspace. Returns None if missing/invalid."""
    output_path = find_router_output(artifacts, workspace, min_mtime=min_mtime)
    if output_path is None:
        return None
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        logger.warning("Failed to parse router output from %s", output_path)
    return None


def validate_questions(raw: list[object]) -> list[str]:
    """Filter and cap elicitation questions. Only keeps non-empty strings."""
    validated: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            validated.append(item.strip())
        if len(validated) >= MAX_QUESTIONS_PER_ROUND:
            break
    return validated


async def collect_elicitation_answers(
    questions: list[str],
    input_reader: InputReader,
    timeout: int = 120,
) -> dict[str, str]:
    """Prompt the user for answers to elicitation questions.

    Each question has a per-input timeout. Uses the injected ``InputReader``
    protocol for testability.

    Returns a dict mapping question text to user answer.
    """
    answers: dict[str, str] = {}
    print("\n    The router has questions before proceeding:")
    print(f"    (each question times out after {timeout}s)\n")
    for i, question in enumerate(questions, 1):
        print(f"    Q{i}: {question}")
        answer = await input_reader.read("    > ", timeout)
        if answer is None:
            print("\n    (input cancelled or timed out — using defaults for remaining)")
            break
        if answer:
            answers[question] = answer
    print()
    return answers


def save_elicitation_context(workspace: Path, context: dict[str, str]) -> None:
    """Save elicitation answers to workspace as JSON artifact.

    Uses atomic write (write-to-tmp + rename) to prevent corrupt partial writes.
    Logs a warning on write failure instead of raising -- elicitation persistence
    is best-effort and must not crash the pipeline.
    """
    artifact_path = workspace / "elicitation-context.json"
    try:
        fd, tmp_path = tempfile.mkstemp(dir=workspace, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2)
            os.replace(tmp_path, artifact_path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
        logger.info("Saved elicitation context to %s", artifact_path.name)
    except OSError as exc:
        logger.warning("Failed to save elicitation context: %s", exc)


def extract_elicitation_questions(
    result: ReflectionResult,
    artifacts: tuple[Path, ...],
    workspace: Path,
    min_mtime: float = 0.0,
) -> list[str] | None:
    """Extract validated elicitation questions from router output.

    Returns a list of question strings if found, or None if the router
    didn't produce actionable questions (genuine failure, missing output, etc.).
    """
    if not result.escalation_needed:
        return None
    router_output = parse_router_output(artifacts, workspace, min_mtime=min_mtime)
    if router_output is None:
        return None
    raw_questions = router_output.get("elicitation_questions", [])
    if not isinstance(raw_questions, list):
        return None
    questions = validate_questions(raw_questions)
    return questions if questions else None


async def _run_router_with_elicitation(
    elicitation: dict[str, str],
    step_file: Path,
    agent_def: Path,
    artifacts: tuple[Path, ...],
    stage_runner: StageRunner,
    gate: GateName,
    gate_criteria: str,
    workspace: Path,
    input_reader: InputReader,
) -> tuple[ReflectionResult, tuple[Path, ...]]:
    """Run the Router stage with an interactive elicitation loop.

    If the router produces elicitation questions, prompts the user via the
    injected ``InputReader`` and re-runs the router with enriched context.
    Max ``MAX_ELICITATION_ROUNDS`` rounds.  Falls back to smart defaults
    in non-interactive environments.

    Always persists accumulated answers on exit (success, escalation, or max rounds).
    """
    accumulated_answers: dict[str, str] = {}
    result: ReflectionResult | None = None
    new_artifacts = artifacts

    try:
        for round_num in range(1, MAX_ELICITATION_ROUNDS + 2):  # +2: initial + max rounds
            context = dict(elicitation)
            if accumulated_answers:
                context["elicitation_answers"] = json.dumps(accumulated_answers)

            request = AgentRequest(
                stage=PipelineStage.ROUTER,
                step_file=step_file,
                agent_definition=agent_def,
                prior_artifacts=new_artifacts,
                elicitation_context=MappingProxyType(context),
            )

            round_epoch = time.time()
            result = await stage_runner.run_stage(request, gate=gate, gate_criteria=gate_criteria)
            new_artifacts = result.artifacts

            questions = extract_elicitation_questions(
                result,
                new_artifacts,
                workspace,
                min_mtime=round_epoch,
            )
            if questions is None:
                return result, new_artifacts

            if round_num > MAX_ELICITATION_ROUNDS:
                print(f"    Max elicitation rounds ({MAX_ELICITATION_ROUNDS}) reached — using defaults")
                return result, new_artifacts

            if not is_interactive():
                print("    Non-interactive mode — skipping elicitation, using defaults")
                return result, new_artifacts

            print(f"    Router needs clarification (round {round_num}/{MAX_ELICITATION_ROUNDS}):")
            answers = await collect_elicitation_answers(questions, input_reader)
            if not answers:
                print("    No answers provided — using defaults")
                return result, new_artifacts

            accumulated_answers.update(answers)
            print("    Re-running router with user answers...")

    finally:
        if accumulated_answers:
            save_elicitation_context(workspace, accumulated_answers)

    # Loop always runs at least once, so result is always set
    if result is None:
        raise RuntimeError("Router produced no result after elicitation loop")
    return result, new_artifacts


class RunElicitationCommand:
    """Run router stage with interactive elicitation loop."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(self, input_reader: InputReader, stage_runner: StageRunner) -> None:
        self._input_reader = input_reader
        self._stage_runner = stage_runner

    @property
    def name(self) -> str:
        return "run-elicitation"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Execute the router stage with elicitation support.

        Reads from context:
            - ``state["step_file"]``: Path to workflow step file
            - ``state["agent_def"]``: Path to agent definition file
            - ``state["gate"]``: GateName for the QA gate
            - ``state["gate_criteria"]``: Gate criteria text
            - ``state["elicitation"]``: Initial elicitation dict

        Updates:
            - ``context.artifacts`` with router result artifacts

        Returns:
            CommandResult with success/failure and result data.
        """
        from pipeline.application.cli.protocols import CommandResult

        workspace = context.require_workspace()
        stage_spec = context.state.stage_spec
        if stage_spec is None:
            return CommandResult(success=False, message="No stage_spec in context state")
        _stage, step_file_name, agent_def_name, gate_name = stage_spec
        step_file = Path(step_file_name)
        agent_def = Path(agent_def_name)
        gate = GateName(gate_name)
        gate_criteria: str = context.state.gate_criteria
        elicitation: dict[str, str] = dict(context.state.elicitation)

        # Forward creative instructions to elicitation context if present
        instructions = context.state.instructions
        if instructions:
            elicitation["instructions"] = instructions

        result, new_artifacts = await _run_router_with_elicitation(
            elicitation=elicitation,
            step_file=step_file,
            agent_def=agent_def,
            artifacts=context.artifacts,
            stage_runner=self._stage_runner,
            gate=gate,
            gate_criteria=gate_criteria,
            workspace=workspace,
            input_reader=self._input_reader,
        )

        context.artifacts = new_artifacts

        if result.escalation_needed:
            return CommandResult(
                success=False,
                message="Router escalated — elicitation did not resolve",
                data={
                    "escalation_needed": True,
                    "attempts": result.attempts,
                    "score": result.best_critique.score,
                },
            )

        return CommandResult(
            success=True,
            message="Router completed successfully",
            data={
                "escalation_needed": False,
                "attempts": result.attempts,
                "score": result.best_critique.score,
            },
        )
