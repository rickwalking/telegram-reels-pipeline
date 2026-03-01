"""Tests for PipelineContext and PipelineState — construction, properties, snapshot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.application.cli.context import PipelineContext, PipelineState

# --- Helpers ---


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


# --- PipelineState ---


class TestPipelineState:
    """Verify PipelineState defaults and mutability."""

    def test_default_construction(self) -> None:
        state = PipelineState()
        assert state.args is None
        assert state.cutaway_specs is None
        assert state.instructions == ""
        assert state.start_stage == 1
        assert state.moments_requested == 1
        assert state.framing_style is None
        assert state.stages == 7
        assert state.target_duration == 90
        assert state.current_stage_num == 0
        assert state.stage_spec is None
        assert state.gate_criteria == ""
        assert state.elicitation == {}
        assert state.veo3_task is None

    def test_fields_are_mutable(self) -> None:
        state = PipelineState()
        state.start_stage = 3
        state.instructions = "make it dramatic"
        assert state.start_stage == 3
        assert state.instructions == "make it dramatic"


# --- PipelineContext ---


class TestPipelineContextConstruction:
    """Verify PipelineContext construction and defaults."""

    def test_minimal_construction(self) -> None:
        """Context can be created with only required fields."""
        ctx = _make_context()
        assert ctx.workspace is None
        assert ctx.artifacts == ()
        assert isinstance(ctx.state, PipelineState)
        assert ctx.youtube_url == ""
        assert ctx.user_message == ""
        assert ctx.max_stages == 0
        assert ctx.timeout_seconds == 300.0

    def test_construction_with_all_fields(self, tmp_path: Path) -> None:
        """Context accepts all optional fields."""
        ctx = _make_context(
            workspace=tmp_path,
            artifacts=(tmp_path / "a.json",),
            youtube_url="https://youtube.com/watch?v=test",
            user_message="hello",
            max_stages=3,
            timeout_seconds=600.0,
            resume_workspace="/tmp/ws",
            start_stage=2,
        )
        assert ctx.workspace == tmp_path
        assert len(ctx.artifacts) == 1
        assert ctx.youtube_url == "https://youtube.com/watch?v=test"
        assert ctx.max_stages == 3
        assert ctx.timeout_seconds == 600.0
        assert ctx.resume_workspace == "/tmp/ws"
        assert ctx.start_stage == 2


class TestPipelineContextHasWorkspace:
    """Verify has_workspace property."""

    def test_false_when_none(self) -> None:
        """has_workspace is False when workspace is None."""
        ctx = _make_context()
        assert ctx.has_workspace is False

    def test_true_when_set(self, tmp_path: Path) -> None:
        """has_workspace is True when workspace is set."""
        ctx = _make_context(workspace=tmp_path)
        assert ctx.has_workspace is True


class TestPipelineContextRequireWorkspace:
    """Verify require_workspace method."""

    def test_returns_path_when_set(self, tmp_path: Path) -> None:
        """require_workspace returns the workspace path."""
        ctx = _make_context(workspace=tmp_path)
        assert ctx.require_workspace() == tmp_path

    def test_raises_when_none(self) -> None:
        """require_workspace raises RuntimeError when workspace is None."""
        ctx = _make_context()
        with pytest.raises(RuntimeError, match="workspace has not been set"):
            ctx.require_workspace()


class TestPipelineContextSnapshot:
    """Verify snapshot method."""

    def test_snapshot_with_workspace(self, tmp_path: Path) -> None:
        """Snapshot includes workspace string and state summary."""
        ctx = _make_context(
            workspace=tmp_path,
            youtube_url="https://example.com",
            user_message="test",
            max_stages=5,
        )
        ctx.state.start_stage = 2
        ctx.state.stages = 5

        snap = ctx.snapshot()

        assert snap["workspace"] == str(tmp_path)
        assert snap["artifacts_count"] == 0
        assert snap["youtube_url"] == "https://example.com"
        assert snap["user_message"] == "test"
        assert snap["max_stages"] == 5
        assert snap["state"]["start_stage"] == 2
        assert snap["state"]["stages"] == 5

    def test_snapshot_without_workspace(self) -> None:
        """Snapshot with None workspace returns None for workspace."""
        ctx = _make_context()
        snap = ctx.snapshot()
        assert snap["workspace"] is None

    def test_snapshot_default_state(self) -> None:
        """Snapshot with default state returns zeros."""
        ctx = _make_context()
        snap = ctx.snapshot()
        assert snap["state"]["current_stage_num"] == 0


class TestPipelineContextMutability:
    """Verify that PipelineContext is mutable for accumulated state."""

    def test_workspace_can_be_set(self, tmp_path: Path) -> None:
        """Workspace can be set after construction."""
        ctx = _make_context()
        ctx.workspace = tmp_path
        assert ctx.workspace == tmp_path
        assert ctx.has_workspace is True

    def test_artifacts_can_be_extended(self, tmp_path: Path) -> None:
        """Artifacts tuple can be replaced."""
        ctx = _make_context()
        ctx.artifacts = (tmp_path / "a.json", tmp_path / "b.json")
        assert len(ctx.artifacts) == 2

    def test_state_fields_can_be_updated(self) -> None:
        """State fields can be mutated."""
        ctx = _make_context()
        ctx.state.instructions = "value"
        assert ctx.state.instructions == "value"
