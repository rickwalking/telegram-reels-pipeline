"""SetupWorkspaceCommand — create or resume a pipeline workspace."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.application.cli.commands.validate_args import (
    ALL_STAGES,
    STAGE_SIGNATURES,
    TOTAL_CLI_STAGES,
)

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import Command, CommandResult

logger = logging.getLogger(__name__)


def _stage_name(stage_num: int) -> str:
    """Return the human-readable display name for a 1-indexed stage number."""
    if 1 <= stage_num <= TOTAL_CLI_STAGES:
        return ALL_STAGES[stage_num - 1][0].value.replace("_", "-")
    return f"stage-{stage_num}"


def print_resume_preflight(workspace: Path, start_stage: int) -> None:
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


class SetupWorkspaceCommand:
    """Create or resume a pipeline workspace."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(self, workspace_base: Path) -> None:
        self._workspace_base = workspace_base

    @property
    def name(self) -> str:
        return "setup-workspace"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Create or resume a workspace and set ``context.workspace``.

        When ``context.resume_workspace`` is set, validates the path and uses it.
        Otherwise, creates a new timestamped directory under ``workspace_base/runs/``.

        On resume, loads existing artifacts from the workspace directory and prints
        a preflight summary. Sets ``context.workspace`` and ``context.artifacts``.
        """
        from pipeline.application.cli.protocols import CommandResult
        from pipeline.application.workspace_manager import WorkspaceManager

        resume_path = context.resume_workspace
        start_stage = context.state.get("start_stage", context.start_stage or 1)

        if resume_path:
            workspace = Path(resume_path) if not isinstance(resume_path, Path) else resume_path
            if not workspace.is_dir():
                return CommandResult(
                    success=False,
                    message=f"Resume workspace is not a valid directory: {workspace}",
                )
            context.workspace = workspace
            logger.info("Resuming workspace: %s", workspace)
            print(f"  Resuming workspace: {workspace}")
            print_resume_preflight(workspace, start_stage)

            # Load existing artifacts when resuming
            if start_stage > 1:
                existing = sorted(p for p in workspace.iterdir() if p.is_file())
                context.artifacts = tuple(existing)
                print(f"  Loaded {len(context.artifacts)} existing artifacts from workspace")
                for a in context.artifacts:
                    print(f"    - {a.name}")
                print()

            return CommandResult(
                success=True,
                message=f"Resumed workspace: {workspace}",
                data={"workspace": str(workspace), "resumed": True},
            )

        # Create new workspace
        workspace_mgr = WorkspaceManager(base_dir=self._workspace_base)
        workspace = workspace_mgr.create_workspace()
        context.workspace = workspace
        logger.info("Created workspace: %s", workspace)
        print(f"  New workspace: {workspace}\n")

        return CommandResult(
            success=True,
            message=f"Created workspace: {workspace}",
            data={"workspace": str(workspace), "resumed": False},
        )
