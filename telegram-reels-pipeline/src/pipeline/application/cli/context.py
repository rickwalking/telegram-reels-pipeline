"""PipelineContext — shared context dataclass replacing run_pipeline() multi-arg signature."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.app.settings import PipelineSettings
    from pipeline.application.event_bus import EventBus
    from pipeline.application.stage_runner import StageRunner


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
    state: dict[str, Any] = field(default_factory=dict)

    # --- Optional overrides ---
    youtube_url: str = ""
    user_message: str = ""
    max_stages: int = 0
    timeout_seconds: float = 300.0
    resume_workspace: str = ""
    start_stage: int = 0

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
            "state_keys": sorted(self.state.keys()),
        }
