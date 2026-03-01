"""ValidateArgsCommand — validate CLI arguments and resolve defaults."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult

logger = logging.getLogger(__name__)

# All pipeline stages in order (delivery skipped -- no Telegram)
ALL_STAGES: tuple[tuple[PipelineStage, str, str, str], ...] = (
    (PipelineStage.ROUTER, "stage-01-router.md", "router", "router"),
    (PipelineStage.RESEARCH, "stage-02-research.md", "research", "research"),
    (PipelineStage.TRANSCRIPT, "stage-03-transcript.md", "transcript", "transcript"),
    (PipelineStage.CONTENT, "stage-04-content.md", "content-creator", "content"),
    (PipelineStage.LAYOUT_DETECTIVE, "stage-05-layout-detective.md", "layout-detective", "layout"),
    (PipelineStage.FFMPEG_ENGINEER, "stage-06-ffmpeg-engineer.md", "ffmpeg-engineer", "ffmpeg"),
    (PipelineStage.ASSEMBLY, "stage-07-assembly.md", "qa", "assembly"),
)

TOTAL_CLI_STAGES: int = len(ALL_STAGES)
_AUTO_TRIGGER_THRESHOLD: int = 120

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

# Style CLI shorthand to domain enum values
STYLE_MAP: dict[str, str] = {
    "split": "split_horizontal",
    "pip": "pip",
    "auto": "auto",
    "default": "default",
}


def compute_moments_requested(target_duration: int, explicit_moments: int | None) -> int:
    """Compute the number of narrative moments to request.

    If ``explicit_moments`` is provided, returns it directly (user override).
    Otherwise, auto-computes from ``target_duration``:
    - ``<= 120s``: 1 moment (single, current behavior)
    - ``> 120s``: ``min(5, max(2, int(target_duration / 60 + 0.5)))``

    Uses ``int(x + 0.5)`` instead of ``round()`` to avoid Python's banker's
    rounding (round-half-to-even), which would map 150s -> 2 instead of 3.
    """
    if explicit_moments is not None:
        return explicit_moments
    if target_duration <= _AUTO_TRIGGER_THRESHOLD:
        return 1
    return min(5, max(2, int(target_duration / 60 + 0.5)))


def detect_resume_stage(workspace_path: Any) -> int | None:
    """Detect the next stage to run by inspecting workspace artifacts.

    Walks stages 1-N checking for signature artifacts. A stage is complete
    when ALL of its signature artifacts exist (e.g., stage 6 requires both
    encoding-plan.json and segment-001.mp4). Returns the first stage number
    whose signatures are incomplete.
    Returns None if no completed stages found (empty workspace).
    """
    from pathlib import Path

    workspace = Path(workspace_path) if not isinstance(workspace_path, Path) else workspace_path
    last_completed = 0
    for stage_num in range(1, TOTAL_CLI_STAGES + 1):
        signatures = STAGE_SIGNATURES.get(stage_num, ())
        if all((workspace / name).exists() for name in signatures):
            last_completed = stage_num
        else:
            break
    return last_completed + 1 if last_completed > 0 else None


def _resolve_start_stage(
    start_stage: int | None,
    resume_path: Any,
) -> tuple[int, bool]:
    """Resolve start stage when not explicitly provided.

    Returns:
        ``(start_stage, all_complete)`` tuple. If ``all_complete`` is True
        the caller should exit early.
    """
    from pathlib import Path

    if start_stage is not None:
        return start_stage, False

    if resume_path is not None:
        workspace = Path(resume_path) if not isinstance(resume_path, Path) else resume_path
        detected = detect_resume_stage(workspace)
        if detected is not None:
            if detected > TOTAL_CLI_STAGES:
                return detected, True  # all stages complete
            if detected > 1:
                print(
                    f"  Auto-detected resume stage: {detected} (override with --start-stage N)",
                    file=sys.stderr,
                )
                return detected, False

    return 1, False


def _validate_ranges(
    start_stage_raw: int | None,
    resume: Any,
    stages: int,
    target_duration: int,
    moments: int | None,
) -> str | None:
    """Check individual argument ranges. Returns error message or None."""
    from pathlib import Path

    if start_stage_raw is not None and (start_stage_raw < 1 or start_stage_raw > TOTAL_CLI_STAGES):
        return f"--start-stage must be between 1 and {TOTAL_CLI_STAGES}, got {start_stage_raw}"

    if resume is not None:
        resume_path = Path(resume) if not isinstance(resume, Path) else resume
        if not resume_path.is_dir():
            return (
                f"--resume path is not a valid directory: {resume}\n"
                f"  Hint: use an existing workspace path, e.g.:\n"
                f"    --resume workspace/runs/20260211-191521-a97fec"
            )

    if start_stage_raw is not None and start_stage_raw > 1 and resume is None:
        return (
            f"--start-stage {start_stage_raw} requires --resume <workspace_path>\n"
            f"  Hint: specify the workspace to resume from, e.g.:\n"
            f"    --resume workspace/runs/<RUN_ID> --start-stage {start_stage_raw}"
        )

    if stages < 1 or stages > TOTAL_CLI_STAGES:
        return f"--stages must be between 1 and {TOTAL_CLI_STAGES}, got {stages}"

    if target_duration < 30 or target_duration > 300:
        return f"--target-duration must be between 30 and 300, got {target_duration}"

    if moments is not None and (moments < 1 or moments > 5):
        return f"--moments must be between 1 and 5, got {moments}"

    return None


class ValidateArgsCommand:
    """Validate CLI arguments and resolve defaults."""

    if TYPE_CHECKING:
        _protocol_check: Command

    @property
    def name(self) -> str:
        return "validate-args"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Validate CLI args from ``context.state["args"]`` and populate context state.

        Reads an ``argparse.Namespace`` from ``context.state["args"]`` and validates
        all argument combinations. On success, sets:
        - ``context.state["start_stage"]``
        - ``context.state["moments_requested"]``
        - ``context.state["framing_style"]``
        - ``context.state["stages"]``
        - ``context.state["target_duration"]``

        Returns ``CommandResult(success=False)`` for validation failures instead of
        calling ``arg_parser.error()`` / ``sys.exit()``.
        """
        from pipeline.application.cli.protocols import CommandResult

        args = context.state.args
        if args is None:
            return CommandResult(success=False, message="No args in context state")

        stages = getattr(args, "stages", 7)
        resume = getattr(args, "resume", None)
        start_stage_raw = getattr(args, "start_stage", None)
        target_duration = getattr(args, "target_duration", 90)
        moments = getattr(args, "moments", None)
        style = getattr(args, "style", None)
        instructions = getattr(args, "instructions", None)

        # Validate individual argument ranges
        error = _validate_ranges(start_stage_raw, resume, stages, target_duration, moments)
        if error is not None:
            return CommandResult(success=False, message=error)

        if instructions is not None and not instructions.strip():
            return CommandResult(success=False, message="--instructions must not be empty when provided")

        # Resolve start stage (auto-detect or default)
        resolved_start, all_complete = _resolve_start_stage(start_stage_raw, resume)
        if all_complete:
            return CommandResult(
                success=True,
                message=f"All {TOTAL_CLI_STAGES} stages already complete in this workspace.",
                data={"exit_early": True},
            )

        # Validate start_stage <= stages
        if resolved_start > stages:
            return CommandResult(
                success=False,
                message=f"--start-stage ({resolved_start}) cannot be greater than --stages ({stages})",
            )

        # Compute moments and map style
        moments_requested = compute_moments_requested(target_duration, moments)
        framing_style = STYLE_MAP.get(style) if style else None

        # Populate context state
        context.state.start_stage = resolved_start
        context.state.moments_requested = moments_requested
        context.state.framing_style = framing_style
        context.state.stages = stages
        context.state.target_duration = target_duration
        context.state.instructions = instructions.strip() if instructions else ""

        return CommandResult(
            success=True,
            message=f"Args validated: start_stage={resolved_start}, moments={moments_requested}",
        )
