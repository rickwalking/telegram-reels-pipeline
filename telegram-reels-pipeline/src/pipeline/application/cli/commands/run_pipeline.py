"""RunPipelineCommand — top-level orchestrator composing sub-commands via PipelineInvoker."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pipeline.application.cli.commands.run_stage import ALL_STAGES, stage_name
from pipeline.application.cli.protocols import CommandResult

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.invoker import PipelineInvoker
    from pipeline.application.cli.protocols import Command

logger = logging.getLogger(__name__)


class RunPipelineCommand:
    """Compose sub-commands into the full pipeline execution sequence.

    Orchestrates: ValidateArgs → SetupWorkspace → DownloadCutaways →
    (RunElicitation | RunStage) × N via the PipelineInvoker.
    """

    if TYPE_CHECKING:
        from pipeline.application.cli.protocols import Command as _Command

        _protocol_check: _Command

    def __init__(
        self,
        invoker: PipelineInvoker,
        validate_cmd: Command,
        setup_cmd: Command,
        download_cmd: Command,
        elicitation_cmd: Command,
        stage_cmd: Command,
    ) -> None:
        self._invoker = invoker
        self._validate_cmd = validate_cmd
        self._setup_cmd = setup_cmd
        self._download_cmd = download_cmd
        self._elicitation_cmd = elicitation_cmd
        self._stage_cmd = stage_cmd

    @property
    def name(self) -> str:
        return "run-pipeline"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Run the full pipeline sequence."""
        # --- Phase 1: Validate arguments ---
        result = await self._invoker.execute(self._validate_cmd, context)
        if not result.success:
            return result
        if result.data.get("exit_early"):
            return result

        # --- Phase 2: Print header ---
        _print_header(context)

        # --- Phase 3: Setup workspace ---
        result = await self._invoker.execute(self._setup_cmd, context)
        if not result.success:
            return result

        # --- Phase 4: Download cutaway clips ---
        result = await self._invoker.execute(self._download_cmd, context)
        if not result.success:
            return result

        # --- Phase 5: Execute stages ---
        overall_start = time.monotonic()
        stages = ALL_STAGES[: context.state.get("stages", 7)]
        start_stage = context.state.get("start_stage", 1)

        for stage_idx, stage_spec in enumerate(stages, 1):
            if stage_idx < start_stage:
                print(f"  [{stage_spec[0].value.upper()}] Skipped (resuming)")
                continue

            stage = stage_spec[0]
            context.state["current_stage_num"] = stage_idx
            context.state["stage_spec"] = stage_spec

            # Router stage uses elicitation command
            from pipeline.domain.enums import PipelineStage

            if stage == PipelineStage.ROUTER:
                result = await self._invoker.execute(self._elicitation_cmd, context)
            else:
                result = await self._invoker.execute(self._stage_cmd, context)

            if not result.success:
                break

            if result.data.get("escalation_needed"):
                print("    ESCALATION needed — stopping.")
                break

        total = time.monotonic() - overall_start
        _print_footer(context, total)

        return CommandResult(success=True, message=f"Pipeline completed in {total:.1f}s")


def _print_header(context: PipelineContext) -> None:
    """Print the pipeline run header."""
    stages_count = context.state.get("stages", 7)
    start_stage = context.state.get("start_stage", 1)
    start_label = stage_name(start_stage)
    target_duration = context.state.get("target_duration", 90)
    moments = context.state.get("moments_requested", 1)

    print(f"\n{'=' * 60}")
    print(f"  PIPELINE RUN — {stages_count} stages (starting at stage {start_stage}: {start_label})")
    print(f"  URL: {context.youtube_url}")
    if context.user_message != context.youtube_url:
        print(f"  Message: {context.user_message}")
    print(f"  Timeout: {context.timeout_seconds}s")
    if target_duration != 90:
        print(f"  Target duration: {target_duration}s (extended narrative)")
    if moments > 1:
        print(f"  Narrative moments: {moments}")
    cutaway_specs = context.state.get("cutaway_specs")
    print(f"  Cutaway clips: {len(cutaway_specs) if cutaway_specs else 0}")
    print(f"{'=' * 60}\n")


def _print_footer(context: PipelineContext, total_seconds: float) -> None:
    """Print the pipeline completion footer with workspace contents."""
    workspace = context.workspace

    print(f"\n{'=' * 60}")
    print(f"  Total time: {total_seconds:.1f}s")
    print(f"  Workspace: {workspace}")
    print(f"{'=' * 60}\n")

    if workspace is not None and workspace.is_dir():
        print("  Workspace contents:")
        for p in sorted(workspace.rglob("*")):
            if p.is_file():
                rel = p.relative_to(workspace)
                size = p.stat().st_size
                print(f"    {rel} ({size} bytes)")
