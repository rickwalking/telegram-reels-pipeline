"""SetupWorkspaceCommand — create or resume a pipeline workspace."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.application.cli.stage_registry import (
    STAGE_SIGNATURES,
    TOTAL_CLI_STAGES,
    stage_name,
)

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult, OutputPort

logger = logging.getLogger(__name__)


def print_resume_preflight(
    workspace: Path,
    start_stage: int,
    output: OutputPort = print,
) -> None:
    """Print a preflight summary of workspace state when resuming."""
    output("  Workspace artifact check:")
    for stage_num in range(1, TOTAL_CLI_STAGES + 1):
        signatures = STAGE_SIGNATURES.get(stage_num, ())
        found = [name for name in signatures if (workspace / name).exists()]
        status = "ok" if found else "missing"
        marker = "  " if stage_num < start_stage else ">>"
        name = stage_name(stage_num)
        if found:
            output(f"    {marker} Stage {stage_num} ({name}): {status} [{', '.join(found)}]")
        else:
            output(f"    {marker} Stage {stage_num} ({name}): {status}")
    output()


class SetupWorkspaceCommand:
    """Create or resume a pipeline workspace."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(self, workspace_base: Path, output: OutputPort = print) -> None:
        self._workspace_base = workspace_base
        self._output = output

    @property
    def name(self) -> str:
        return "setup-workspace"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Create or resume a workspace and set ``context.workspace``."""
        from pipeline.application.cli.protocols import CommandResult
        from pipeline.application.workspace_manager import WorkspaceManager

        resume_path = context.resume_workspace
        start_stage = context.state.start_stage or context.start_stage or 1

        if resume_path:
            return await self._resume(context, resume_path, start_stage)

        # Create new workspace
        workspace_mgr = WorkspaceManager(base_dir=self._workspace_base)
        workspace = workspace_mgr.create_workspace()
        context.set_workspace(workspace)
        logger.info("Created workspace: %s", workspace)
        self._output(f"  New workspace: {workspace}\n")

        return CommandResult(
            success=True,
            message=f"Created workspace: {workspace}",
            data={"workspace": str(workspace), "resumed": False},
        )

    async def _resume(
        self,
        context: PipelineContext,
        resume_path: str,
        start_stage: int,
    ) -> CommandResult:
        """Resume an existing workspace."""
        from pipeline.application.cli.protocols import CommandResult

        workspace = Path(resume_path) if not isinstance(resume_path, Path) else resume_path
        if not workspace.is_dir():
            return CommandResult(
                success=False,
                message=f"Resume workspace is not a valid directory: {workspace}",
            )
        context.set_workspace(workspace)
        logger.info("Resuming workspace: %s", workspace)
        self._output(f"  Resuming workspace: {workspace}")
        print_resume_preflight(workspace, start_stage, output=self._output)

        # Load existing artifacts when resuming
        if start_stage > 1:
            existing = sorted(p for p in workspace.iterdir() if p.is_file())
            context.artifacts = tuple(existing)
            self._output(f"  Loaded {len(context.artifacts)} existing artifacts from workspace")
            for a in context.artifacts:
                self._output(f"    - {a.name}")
            self._output("")

        return CommandResult(
            success=True,
            message=f"Resumed workspace: {workspace}",
            data={"workspace": str(workspace), "resumed": True},
        )
