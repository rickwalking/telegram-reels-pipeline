"""PipelineContext — shared context dataclass replacing run_pipeline() multi-arg signature."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    import asyncio

    from pipeline.app.settings import PipelineSettings
    from pipeline.application.event_bus import EventBus
    from pipeline.application.stage_runner import StageRunner


@dataclass
class PipelineState:
    """Typed state accumulated during pipeline CLI execution.

    Replaces the untyped ``dict[str, Any]`` with explicit fields so that
    inter-command contracts are enforced at the type level.
    """

    # --- Set by composition root (run_cli.py) ---
    args: Any = None  # argparse.Namespace, consumed only by ValidateArgs
    cutaway_specs: list[str] | None = None
    instructions: str = ""

    # --- Set by ValidateArgsCommand ---
    start_stage: int = 1
    moments_requested: int = 1
    framing_style: str | None = None
    stages: int = 7
    target_duration: int = 90

    # --- Set per-stage by RunPipelineCommand ---
    current_stage_num: int = 0
    stage_spec: tuple[PipelineStage, str, str, str] | None = None

    # --- Set by RunStageCommand / RunElicitationCommand ---
    gate_criteria: str = ""
    elicitation: dict[str, str] = field(default_factory=dict)

    # --- Set by Veo3FireHook ---
    veo3_task: asyncio.Task[None] | None = None


@dataclass
class PipelineContext:
    """Shared execution context for all CLI commands.

    Replaces the 11-argument ``run_pipeline()`` signature with a single
    injectable object.  Mutable fields (``workspace``, ``artifacts``,
    ``state``) are accumulated during execution.
    """

    # --- Injected at construction (required) ---
    settings: PipelineSettings
    stage_runner: StageRunner
    event_bus: EventBus

    # --- Accumulated during execution ---
    workspace: Path | None = None
    artifacts: tuple[Path, ...] = field(default_factory=tuple)
    state: PipelineState = field(default_factory=PipelineState)

    # --- Path resolution ---
    project_root: Path = Path()

    # --- Workspace lifecycle callback ---
    _on_workspace_set: Callable[[Path | None], None] | None = field(default=None, repr=False)

    # --- Optional overrides ---
    youtube_url: str = ""
    user_message: str = ""
    max_stages: int = 0
    timeout_seconds: float = 300.0
    resume_workspace: str = ""
    start_stage: int = 0

    def set_workspace(self, workspace: Path | None) -> None:
        """Set workspace and notify infrastructure via callback."""
        self.workspace = workspace
        if self._on_workspace_set is not None:
            self._on_workspace_set(workspace)

    @property
    def has_workspace(self) -> bool:
        """True when a workspace directory has been set."""
        return self.workspace is not None

    def require_workspace(self) -> Path:
        """Return workspace path or raise if not set.

        Raises:
            RuntimeError: If workspace has not been set yet.
        """
        if self.workspace is None:
            raise RuntimeError("workspace has not been set — run setup command first")
        return self.workspace

    def snapshot(self) -> dict[str, Any]:
        """Capture current context state for history recording."""
        return {
            "workspace": str(self.workspace) if self.workspace else None,
            "artifacts_count": len(self.artifacts),
            "youtube_url": self.youtube_url,
            "user_message": self.user_message,
            "max_stages": self.max_stages,
            "state": {
                "start_stage": self.state.start_stage,
                "stages": self.state.stages,
                "current_stage_num": self.state.current_stage_num,
            },
        }
