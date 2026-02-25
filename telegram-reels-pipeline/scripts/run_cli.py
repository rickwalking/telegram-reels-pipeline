"""CLI pipeline runner — run the full pipeline from a terminal (no Telegram).

Usage::

    poetry run python scripts/run_cli.py [youtube_url] [--message "user message"]
    poetry run python scripts/run_cli.py [youtube_url] [--stages 3]
    poetry run python scripts/run_cli.py [youtube_url] --timeout 600
    poetry run python scripts/run_cli.py [youtube_url] --resume /path/to/workspace --start-stage 6
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from types import MappingProxyType

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.app.settings import PipelineSettings
from pipeline.application.event_bus import EventBus
from pipeline.application.recovery_chain import RecoveryChain
from pipeline.application.reflection_loop import ReflectionLoop
from pipeline.application.stage_runner import StageRunner
from pipeline.application.workspace_manager import WorkspaceManager
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest, ReflectionResult
from pipeline.domain.types import GateName
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend
from pipeline.infrastructure.adapters.ffmpeg_adapter import FFmpegAdapter
from pipeline.infrastructure.adapters.gemini_veo3_adapter import GeminiVeo3Adapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("run_cli")

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

DEFAULT_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
MAX_ELICITATION_ROUNDS: int = 2
MAX_QUESTIONS_PER_ROUND: int = 5
INPUT_TIMEOUT_SECONDS: int = 120
MTIME_TOLERANCE_SECONDS: float = 2.0
TOTAL_CLI_STAGES: int = len(ALL_STAGES)
_AUTO_TRIGGER_THRESHOLD: int = 120


def compute_moments_requested(target_duration: int, explicit_moments: int | None) -> int:
    """Compute the number of narrative moments to request.

    If ``explicit_moments`` is provided, returns it directly (user override).
    Otherwise, auto-computes from ``target_duration``:
    - ``<= 120s``: 1 moment (single, current behavior)
    - ``> 120s``: ``min(5, max(2, int(target_duration / 60 + 0.5)))``

    Uses ``int(x + 0.5)`` instead of ``round()`` to avoid Python's banker's
    rounding (round-half-to-even), which would map 150s → 2 instead of 3.
    """
    if explicit_moments is not None:
        return explicit_moments
    if target_duration <= _AUTO_TRIGGER_THRESHOLD:
        return 1
    return min(5, max(2, int(target_duration / 60 + 0.5)))


# Signature artifacts per stage (1-indexed). A stage is "complete" if at least
# one of its signature artifacts exists in the workspace.
STAGE_SIGNATURES: dict[int, tuple[str, ...]] = {
    1: ("router-output.json",),
    2: ("research-output.json",),
    3: ("moment-selection.json",),
    4: ("content.json",),
    5: ("layout-analysis.json",),
    6: ("encoding-plan.json", "segment-001.mp4"),
    7: ("final-reel.mp4",),
}


def _detect_resume_stage(workspace: Path) -> int | None:
    """Detect the next stage to run by inspecting workspace artifacts.

    Walks stages 1-N checking for signature artifacts. A stage is complete
    when ALL of its signature artifacts exist (e.g., stage 6 requires both
    encoding-plan.json and segment-001.mp4). Returns the first stage number
    whose signatures are incomplete.
    Returns None if no completed stages found (empty workspace).
    """
    last_completed = 0
    for stage_num in range(1, TOTAL_CLI_STAGES + 1):
        signatures = STAGE_SIGNATURES.get(stage_num, ())
        if all((workspace / name).exists() for name in signatures):
            last_completed = stage_num
        else:
            break
    return last_completed + 1 if last_completed > 0 else None


def _resolve_start_stage(args: argparse.Namespace) -> None:
    """Auto-detect or default the start stage when not explicitly provided.

    When ``--resume`` is given without ``--start-stage``, inspects workspace
    artifacts to determine where to resume. Exits with code 0 if all stages
    are already complete.
    """
    if args.start_stage is not None:
        return  # Explicitly set — nothing to resolve

    if args.resume is not None:
        detected = _detect_resume_stage(args.resume)
        if detected is not None:
            if detected > TOTAL_CLI_STAGES:
                print(
                    f"  All {TOTAL_CLI_STAGES} stages already complete in this workspace.",
                    file=sys.stderr,
                )
                sys.exit(0)
            if detected > 1:
                args.start_stage = detected
                print(
                    f"  Auto-detected resume stage: {detected} " f"(override with --start-stage N)",
                    file=sys.stderr,
                )
                return

    args.start_stage = 1


def _validate_cli_args(args: argparse.Namespace, *, arg_parser: argparse.ArgumentParser) -> None:
    """Validate CLI argument combinations. Exits with error on invalid input.

    Handles ``--start-stage`` default: argparse stores ``None`` when the flag
    is omitted, allowing us to distinguish "not set" from "explicitly set to 1".
    """
    start_stage_explicit = args.start_stage is not None

    if start_stage_explicit and (args.start_stage < 1 or args.start_stage > TOTAL_CLI_STAGES):
        arg_parser.error(f"--start-stage must be between 1 and {TOTAL_CLI_STAGES}, got {args.start_stage}")

    if args.resume is not None and not args.resume.is_dir():
        arg_parser.error(
            f"--resume path is not a valid directory: {args.resume}\n"
            f"  Hint: use an existing workspace path, e.g.:\n"
            f"    --resume workspace/runs/20260211-191521-a97fec"
        )

    if start_stage_explicit and args.start_stage > 1 and args.resume is None:
        arg_parser.error(
            f"--start-stage {args.start_stage} requires --resume <workspace_path>\n"
            f"  Hint: specify the workspace to resume from, e.g.:\n"
            f"    --resume workspace/runs/<RUN_ID> --start-stage {args.start_stage}"
        )

    if args.stages < 1 or args.stages > TOTAL_CLI_STAGES:
        arg_parser.error(f"--stages must be between 1 and {TOTAL_CLI_STAGES}, got {args.stages}")

    if args.target_duration < 30 or args.target_duration > 300:
        arg_parser.error(f"--target-duration must be between 30 and 300, got {args.target_duration}")

    if args.moments is not None and (args.moments < 1 or args.moments > 5):
        arg_parser.error(f"--moments must be between 1 and 5, got {args.moments}")

    _resolve_start_stage(args)

    if args.start_stage > args.stages:
        arg_parser.error(f"--start-stage ({args.start_stage}) cannot be greater than --stages ({args.stages})")


def _stage_name(stage_num: int) -> str:
    """Return the human-readable display name for a 1-indexed stage number."""
    if 1 <= stage_num <= TOTAL_CLI_STAGES:
        return ALL_STAGES[stage_num - 1][0].value.replace("_", "-")
    return f"stage-{stage_num}"


def _print_resume_preflight(workspace: Path, start_stage: int) -> None:
    """Print a preflight summary of workspace state when resuming."""
    print("  Workspace artifact check:")
    for stage_num in range(1, TOTAL_CLI_STAGES + 1):
        signatures = STAGE_SIGNATURES.get(stage_num, ())
        found = [name for name in signatures if (workspace / name).exists()]
        status = "ok" if found else "missing"
        marker = "  " if stage_num < start_stage else ">>"
        name = _stage_name(stage_num)
        if found:
            print(f"    {marker} Stage {stage_num} ({name}): {status} [{', '.join(found)}]")
        else:
            print(f"    {marker} Stage {stage_num} ({name}): {status}")
    print()


def _is_interactive() -> bool:
    """Check if stdin is an interactive terminal (TTY)."""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def _find_router_output(
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
    # Tolerance for filesystem mtime resolution differences (FAT32 = 2s, ext3 = 1s)
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


def _parse_router_output(
    artifacts: tuple[Path, ...],
    workspace: Path,
    min_mtime: float = 0.0,
) -> dict[str, object] | None:
    """Parse router-output.json from artifacts or workspace. Returns None if missing/invalid."""
    output_path = _find_router_output(artifacts, workspace, min_mtime=min_mtime)
    if output_path is None:
        return None
    try:
        data = json.loads(output_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        logger.warning("Failed to parse router output from %s", output_path)
    return None


async def _timed_input(prompt: str, timeout: int = INPUT_TIMEOUT_SECONDS) -> str | None:
    """Read a line from stdin with a timeout.

    Runs input() in a background thread via asyncio.to_thread so the event loop
    stays responsive. Uses asyncio.wait_for for timeout enforcement.

    Returns the stripped input string, or None on timeout/EOF/interrupt.
    """
    try:
        raw = await asyncio.wait_for(asyncio.to_thread(input, prompt), timeout=timeout)
        return raw.strip()
    except (TimeoutError, EOFError, KeyboardInterrupt):
        return None


def _validate_questions(raw: list[object]) -> list[str]:
    """Filter and cap elicitation questions. Only keeps non-empty strings."""
    validated: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            validated.append(item.strip())
        if len(validated) >= MAX_QUESTIONS_PER_ROUND:
            break
    return validated


async def _collect_elicitation_answers(questions: list[str]) -> dict[str, str]:
    """Prompt the user for answers to elicitation questions via stdin.

    Each question has a per-input timeout of INPUT_TIMEOUT_SECONDS.
    Returns a dict mapping question text to user answer.
    """
    answers: dict[str, str] = {}
    print("\n    The router has questions before proceeding:")
    print(f"    (each question times out after {INPUT_TIMEOUT_SECONDS}s)\n")
    for i, question in enumerate(questions, 1):
        print(f"    Q{i}: {question}")
        answer = await _timed_input("    > ")
        if answer is None:
            print("\n    (input cancelled or timed out — using defaults for remaining)")
            break
        if answer:
            answers[question] = answer
    print()
    return answers


def _save_elicitation_context(workspace: Path, context: dict[str, str]) -> None:
    """Save elicitation answers to workspace as JSON artifact.

    Uses atomic write (write-to-tmp + rename) to prevent corrupt partial writes.
    Logs a warning on write failure instead of raising — elicitation persistence
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


def _extract_elicitation_questions(
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
    router_output = _parse_router_output(artifacts, workspace, min_mtime=min_mtime)
    if router_output is None:
        return None
    raw_questions = router_output.get("elicitation_questions", [])
    if not isinstance(raw_questions, list):
        return None
    questions = _validate_questions(raw_questions)
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
) -> tuple[ReflectionResult, tuple[Path, ...]]:
    """Run the Router stage with an interactive elicitation loop.

    If the router produces elicitation questions, prompts the user via stdin
    and re-runs the router with enriched context. Max MAX_ELICITATION_ROUNDS rounds.
    Falls back to smart defaults in non-interactive environments.

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

            questions = _extract_elicitation_questions(
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

            if not _is_interactive():
                print("    Non-interactive mode — skipping elicitation, using defaults")
                return result, new_artifacts

            print(f"    Router needs clarification (round {round_num}/{MAX_ELICITATION_ROUNDS}):")
            answers = await _collect_elicitation_answers(questions)
            if not answers:
                print("    No answers provided — using defaults")
                return result, new_artifacts

            accumulated_answers.update(answers)
            print("    Re-running router with user answers...")

    finally:
        if accumulated_answers:
            _save_elicitation_context(workspace, accumulated_answers)

    # Loop always runs at least once, so result is always set
    if result is None:
        raise RuntimeError("Router produced no result after elicitation loop")
    return result, new_artifacts


def _build_veo3_adapter(settings: PipelineSettings) -> GeminiVeo3Adapter | None:
    """Construct the Veo3 adapter if a Gemini API key is configured."""
    if not settings.gemini_api_key:
        return None
    logger.info("Veo3 adapter initialized (Gemini API key present)")
    return GeminiVeo3Adapter(api_key=settings.gemini_api_key)


def _fire_veo3_background(
    adapter: GeminiVeo3Adapter,
    workspace: Path,
    settings: PipelineSettings,
) -> asyncio.Task[None] | None:
    """Create a Veo3Orchestrator and fire start_generation as a background task.

    Returns the task handle, or None on setup failure. Failures are logged
    but never crash the pipeline.
    """
    try:
        from pipeline.application.veo3_orchestrator import Veo3Orchestrator

        orchestrator = Veo3Orchestrator(
            video_gen=adapter,
            clip_count=settings.veo3_clip_count,
            timeout_s=settings.veo3_timeout_s,
        )
        run_id = workspace.name
        task: asyncio.Task[None] = asyncio.create_task(
            orchestrator.start_generation(workspace, run_id),
            name=f"veo3-gen-{run_id}",
        )
        logger.info("Veo3 background generation fired for run %s", run_id)
        print("  [VEO3] Background generation started")
        return task
    except Exception:
        logger.warning("Veo3 generation fire failed — continuing pipeline", exc_info=True)
        print("  [VEO3] Generation fire failed — continuing without B-roll")
        return None


async def _run_veo3_await_gate(
    veo3_task: asyncio.Task[None] | None,
    adapter: GeminiVeo3Adapter | None,
    workspace: Path,
    settings: PipelineSettings,
) -> None:
    """Await Veo3 background generation and run the polling gate.

    Failures are logged but never crash the pipeline (graceful degradation).
    """
    from pipeline.application.veo3_await_gate import run_veo3_await_gate
    from pipeline.application.veo3_orchestrator import Veo3Orchestrator

    print("  [VEO3] Awaiting generation completion...")
    try:
        if veo3_task is not None:
            try:
                await veo3_task
            except Exception:
                logger.warning("Veo3 background task failed", exc_info=True)
                print("  [VEO3] Background task failed — checking partial results")

        orchestrator = None
        if adapter is not None:
            orchestrator = Veo3Orchestrator(
                video_gen=adapter,
                clip_count=settings.veo3_clip_count,
                timeout_s=settings.veo3_timeout_s,
            )

        summary = await run_veo3_await_gate(
            workspace=workspace,
            orchestrator=orchestrator,
            timeout_s=settings.veo3_timeout_s,
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


async def _run_stages(
    stages: tuple[tuple[PipelineStage, str, str, str], ...],
    start_stage: int,
    workflows_dir: Path,
    agents_dir: Path,
    url: str,
    message: str,
    stage_runner: StageRunner,
    workspace: Path,
    artifacts: tuple[Path, ...],
    settings: PipelineSettings,
    framing_style: str | None = None,
    target_duration_seconds: int = 90,
    moments_requested: int = 1,
    veo3_adapter: GeminiVeo3Adapter | None = None,
) -> tuple[Path, ...]:
    """Execute pipeline stages sequentially with router elicitation support."""
    veo3_task: asyncio.Task[None] | None = None

    for stage_idx, (stage, step_file_name, agent_dir, gate_name) in enumerate(stages, 1):
        if stage_idx < start_stage:
            print(f"  [{stage.value.upper()}] Skipped (resuming)")
            continue
        step_file = workflows_dir / "stages" / step_file_name
        agent_def = agents_dir / agent_dir / "agent.md"

        if not step_file.exists():
            print(f"  [SKIP] {stage.value}: step file missing ({step_file})")
            continue
        if not agent_def.exists():
            print(f"  [SKIP] {stage.value}: agent definition missing ({agent_def})")
            continue

        elicitation: dict[str, str] = {}
        if stage == PipelineStage.ROUTER:
            if url not in message:
                elicitation["telegram_message"] = f"{url} {message}"
            else:
                elicitation["telegram_message"] = message
        elif stage == PipelineStage.CONTENT:
            if settings.publishing_language:
                elicitation["publishing_language"] = settings.publishing_language
                elicitation["publishing_description_variants"] = str(settings.publishing_description_variants)

        if framing_style:
            elicitation["framing_style"] = framing_style

        if target_duration_seconds != 90:
            elicitation["target_duration_seconds"] = str(target_duration_seconds)

        if moments_requested > 1:
            elicitation["moments_requested"] = str(moments_requested)

        criteria_path = workflows_dir / "qa" / "gate-criteria" / f"{gate_name}-criteria.md"
        gate_criteria = criteria_path.read_text() if criteria_path.exists() else ""

        print(f"  [{stage.value.upper()}] Starting...")
        stage_start = time.monotonic()

        try:
            # Pre-stage hook: await Veo3 generation before Assembly
            if stage == PipelineStage.ASSEMBLY and veo3_task is not None:
                await _run_veo3_await_gate(veo3_task, veo3_adapter, workspace, settings)
                veo3_task = None

            if stage == PipelineStage.ROUTER:
                result, artifacts = await _run_router_with_elicitation(
                    elicitation=elicitation,
                    step_file=step_file,
                    agent_def=agent_def,
                    artifacts=artifacts,
                    stage_runner=stage_runner,
                    gate=GateName(gate_name),
                    gate_criteria=gate_criteria,
                    workspace=workspace,
                )
            else:
                request = AgentRequest(
                    stage=stage,
                    step_file=step_file,
                    agent_definition=agent_def,
                    prior_artifacts=artifacts,
                    elicitation_context=MappingProxyType(elicitation),
                )
                result = await stage_runner.run_stage(
                    request,
                    gate=GateName(gate_name),
                    gate_criteria=gate_criteria,
                )
                artifacts = result.artifacts

            if result.escalation_needed:
                elapsed = time.monotonic() - stage_start
                _print_stage_result(stage, result, artifacts, elapsed)
                print("    ESCALATION needed — stopping.")
                break

            # Post-stage hook: fire Veo3 background generation after Content stage
            if stage == PipelineStage.CONTENT and veo3_adapter is not None:
                veo3_task = _fire_veo3_background(veo3_adapter, workspace, settings)

            # Post-stage hook: execute encoding plan after FFmpeg Engineer plans commands
            if stage == PipelineStage.FFMPEG_ENGINEER:
                plan_path = workspace / "encoding-plan.json"
                if not plan_path.exists():
                    raise RuntimeError("FFmpeg Engineer completed but encoding-plan.json is missing")
                print("  [FFMPEG_ADAPTER] Executing encoding plan...")
                adapter = FFmpegAdapter()
                segments = await adapter.execute_encoding_plan(plan_path, workspace=workspace)
                print(f"  [FFMPEG_ADAPTER] Produced {len(segments)} segments")
                for seg in segments:
                    print(f"      - {seg.name}")
                # Re-collect artifacts so downstream stages see the segment files
                from pipeline.infrastructure.adapters.artifact_collector import collect_artifacts

                artifacts = collect_artifacts(workspace)

            elapsed = time.monotonic() - stage_start
            _print_stage_result(stage, result, artifacts, elapsed)

        except Exception as exc:
            elapsed = time.monotonic() - stage_start
            print(f"  [{stage.value.upper()}] FAILED after {elapsed:.1f}s")
            print(f"    Error: {exc}")
            break

        print()

    return artifacts


def _print_stage_result(
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


async def run_pipeline(
    url: str,
    message: str,
    max_stages: int,
    timeout_seconds: float | None = None,
    resume_workspace: Path | None = None,
    start_stage: int = 1,
    framing_style: str | None = None,
    target_duration_seconds: int = 90,
    verbose: bool = False,
    moments_requested: int = 1,
) -> None:
    settings = PipelineSettings()
    project_root = Path(__file__).resolve().parent.parent

    workflows_dir = project_root / "workflows"
    agents_dir = project_root / "agents"

    effective_timeout = timeout_seconds or settings.agent_timeout_seconds
    settings_style = settings.default_framing_style if settings.default_framing_style != "default" else None
    effective_style = framing_style or settings_style

    cli_backend = CliBackend(
        work_dir=project_root,
        timeout_seconds=effective_timeout,
        dispatch_timeout_seconds=max(300.0, effective_timeout / 2),
        verbose=verbose,
        qa_via_clink=settings.qa_via_clink,
    )
    event_bus = EventBus()
    recovery_chain = RecoveryChain(agent_port=cli_backend)
    reflection_loop = ReflectionLoop(
        agent_port=cli_backend,
        model_port=cli_backend,
        min_score_threshold=settings.min_qa_score,
    )
    stage_runner = StageRunner(
        reflection_loop=reflection_loop,
        recovery_chain=recovery_chain,
        event_bus=event_bus,
    )
    workspace_mgr = WorkspaceManager(base_dir=project_root / "workspace")

    stages = ALL_STAGES[:max_stages]

    # Veo3 adapter — only when API key is configured
    veo3_adapter = _build_veo3_adapter(settings)

    start_label = _stage_name(start_stage)
    print(f"\n{'='*60}")
    print(f"  PIPELINE RUN — {len(stages)} stages (starting at stage {start_stage}: {start_label})")
    print(f"  URL: {url}")
    if message != url:
        print(f"  Message: {message}")
    print(f"  Timeout: {effective_timeout}s")
    if target_duration_seconds != 90:
        print(f"  Target duration: {target_duration_seconds}s (extended narrative)")
    if moments_requested > 1:
        print(f"  Narrative moments: {moments_requested}")
    print(f"{'='*60}\n")

    if resume_workspace is not None:
        if not resume_workspace.is_dir():
            raise ValueError(f"Resume workspace is not a valid directory: {resume_workspace}")
        workspace = resume_workspace
        print(f"  Resuming workspace: {workspace}")
        _print_resume_preflight(workspace, start_stage)
    else:
        workspace = workspace_mgr.create_workspace()
        print(f"  New workspace: {workspace}\n")

    cli_backend.set_workspace(workspace)

    # Collect existing artifacts from workspace when resuming
    artifacts: tuple[Path, ...] = ()
    if start_stage > 1:
        existing = sorted(p for p in workspace.iterdir() if p.is_file())
        artifacts = tuple(existing)
        print(f"  Loaded {len(artifacts)} existing artifacts from workspace")
        for a in artifacts:
            print(f"    - {a.name}")
        print()

    overall_start = time.monotonic()

    try:
        artifacts = await _run_stages(
            stages,
            start_stage,
            workflows_dir,
            agents_dir,
            url,
            message,
            stage_runner,
            workspace,
            artifacts,
            settings,
            framing_style=effective_style,
            target_duration_seconds=target_duration_seconds,
            moments_requested=moments_requested,
            veo3_adapter=veo3_adapter,
        )
    finally:
        cli_backend.set_workspace(None)

    total = time.monotonic() - overall_start
    print(f"\n{'='*60}")
    print(f"  Total time: {total:.1f}s")
    print(f"  Workspace: {workspace}")
    print(f"{'='*60}\n")

    # Show workspace contents
    print("  Workspace contents:")
    for p in sorted(workspace.rglob("*")):
        if p.is_file():
            rel = p.relative_to(workspace)
            size = p.stat().st_size
            print(f"    {rel} ({size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline run (no Telegram delivery)")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="YouTube URL")
    parser.add_argument("--message", "-m", default=None, help="Simulated Telegram message")
    parser.add_argument("--stages", "-s", type=int, default=7, help="Max stages to run (default: 7)")
    parser.add_argument("--timeout", "-t", type=float, default=None, help="Agent timeout in seconds")
    parser.add_argument("--resume", type=Path, default=None, help="Resume from existing workspace path")
    parser.add_argument("--start-stage", type=int, default=None, help="Stage number to start from (1-7, default: 1)")
    parser.add_argument(
        "--style", default=None, choices=["default", "split", "pip", "auto"], help="Framing style for the reel"
    )
    parser.add_argument(
        "--target-duration",
        type=int,
        default=90,
        help="Target duration in seconds (default: 90, max: 300). Longer durations use multi-moment narrative.",
    )
    parser.add_argument(
        "--moments",
        type=int,
        default=None,
        help="Number of narrative moments (1-5). Auto-computed from target-duration when omitted.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print Claude agent output to terminal")
    args = parser.parse_args()

    _validate_cli_args(args, arg_parser=parser)

    # Map CLI shorthand to domain enum values
    style_map = {"split": "split_horizontal", "pip": "pip", "auto": "auto", "default": "default"}
    framing_style = style_map.get(args.style) if args.style else None

    moments = compute_moments_requested(args.target_duration, args.moments)

    message = args.message if args.message else args.url
    asyncio.run(
        run_pipeline(
            args.url,
            message,
            args.stages,
            args.timeout,
            args.resume,
            args.start_stage,
            framing_style,
            args.target_duration,
            verbose=args.verbose,
            moments_requested=moments,
        )
    )


if __name__ == "__main__":
    main()
