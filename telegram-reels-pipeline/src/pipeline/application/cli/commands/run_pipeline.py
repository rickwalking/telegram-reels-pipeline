"""RunPipelineCommand — top-level orchestrator composing sub-commands via PipelineInvoker."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from pipeline.application.cli.protocols import CommandResult
from pipeline.application.cli.stage_registry import ALL_STAGES, stage_name

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.invoker import PipelineInvoker
    from pipeline.application.cli.protocols import Command, OutputPort

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
        output: OutputPort = print,
    ) -> None:
        self._invoker = invoker
        self._validate_cmd = validate_cmd
        self._setup_cmd = setup_cmd
        self._download_cmd = download_cmd
        self._elicitation_cmd = elicitation_cmd
        self._stage_cmd = stage_cmd
        self._output = output

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
        _print_header(context, output=self._output)

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
        stages = ALL_STAGES[: context.state.stages]
        start_stage = context.state.start_stage

        for stage_idx, stage_spec in enumerate(stages, 1):
            if stage_idx < start_stage:
                self._output(f"  [{stage_spec[0].value.upper()}] Skipped (resuming)")
                continue

            stage = stage_spec[0]
            context.state.current_stage_num = stage_idx
            context.state.stage_spec = stage_spec

            # Router stage uses elicitation command
            from pipeline.domain.enums import PipelineStage

            if stage == PipelineStage.ROUTER:
                result = await self._invoker.execute(self._elicitation_cmd, context)
            else:
                result = await self._invoker.execute(self._stage_cmd, context)

            if not result.success:
                break

            if result.data.get("escalation_needed"):
                self._output("    ESCALATION needed — stopping.")
                break

        total = time.monotonic() - overall_start
        _print_footer(context, total, output=self._output)

        return CommandResult(success=True, message=f"Pipeline completed in {total:.1f}s")


def _print_header(context: PipelineContext, output: OutputPort = print) -> None:
    """Print the pipeline run header."""
    stages_count = context.state.stages
    start_stage = context.state.start_stage
    start_label = stage_name(start_stage)
    target_duration = context.state.target_duration
    moments = context.state.moments_requested

    output(f"\n{'=' * 60}")
    output(f"  PIPELINE RUN — {stages_count} stages (starting at stage {start_stage}: {start_label})")
    output(f"  URL: {context.youtube_url}")
    if context.user_message != context.youtube_url:
        output(f"  Message: {context.user_message}")
    output(f"  Timeout: {context.timeout_seconds}s")
    if target_duration != 90:
        output(f"  Target duration: {target_duration}s (extended narrative)")
    if moments > 1:
        output(f"  Narrative moments: {moments}")
    cutaway_specs = context.state.cutaway_specs
    output(f"  Cutaway clips: {len(cutaway_specs) if cutaway_specs else 0}")
    output(f"{'=' * 60}\n")


def _print_footer(context: PipelineContext, total_seconds: float, output: OutputPort = print) -> None:
    """Print the pipeline completion footer with workspace contents."""
    workspace = context.workspace

    output(f"\n{'=' * 60}")
    output(f"  Total time: {total_seconds:.1f}s")
    output(f"  Workspace: {workspace}")
    output(f"{'=' * 60}\n")

    if workspace is not None and workspace.is_dir():
        output("  Workspace contents:")
        for p in sorted(workspace.rglob("*")):
            if p.is_file():
                rel = p.relative_to(workspace)
                size = p.stat().st_size
                output(f"    {rel} ({size} bytes)")
