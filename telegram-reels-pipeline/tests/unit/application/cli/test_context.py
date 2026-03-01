"""Tests for PipelineContext — construction, properties, snapshot."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.application.cli.context import PipelineContext

# --- Helpers ---


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


# --- Tests ---


class TestPipelineContextConstruction:
    """Verify PipelineContext construction and defaults."""

    def test_minimal_construction(self) -> None:
        """Context can be created with only required fields."""
        ctx = _make_context()
        assert ctx.workspace is None
        assert ctx.artifacts == ()
        assert ctx.state == {}
        assert ctx.youtube_url == ""
        assert ctx.user_message == ""
        assert ctx.max_stages == 0
        assert ctx.timeout_seconds == 300.0

    def test_construction_with_all_fields(self, tmp_path: Path) -> None:
        """Context accepts all optional fields."""
        ctx = _make_context(
            workspace=tmp_path,
            artifacts=(tmp_path / "a.json",),
            state={"key": "val"},
            youtube_url="https://youtube.com/watch?v=test",
            user_message="hello",
            max_stages=3,
            timeout_seconds=600.0,
            resume_workspace="/tmp/ws",
            start_stage=2,
        )
        assert ctx.workspace == tmp_path
        assert len(ctx.artifacts) == 1
        assert ctx.state == {"key": "val"}
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
        """Snapshot includes workspace string and state keys."""
        ctx = _make_context(
            workspace=tmp_path,
            youtube_url="https://example.com",
            user_message="test",
            max_stages=5,
        )
        ctx.state["foo"] = "bar"
        ctx.state["baz"] = 42

        snap = ctx.snapshot()

        assert snap["workspace"] == str(tmp_path)
        assert snap["artifacts_count"] == 0
        assert snap["youtube_url"] == "https://example.com"
        assert snap["user_message"] == "test"
        assert snap["max_stages"] == 5
        assert snap["state_keys"] == ["baz", "foo"]

    def test_snapshot_without_workspace(self) -> None:
        """Snapshot with None workspace returns None for workspace."""
        ctx = _make_context()
        snap = ctx.snapshot()
        assert snap["workspace"] is None

    def test_snapshot_empty_state(self) -> None:
        """Snapshot with empty state returns empty state_keys."""
        ctx = _make_context()
        snap = ctx.snapshot()
        assert snap["state_keys"] == []


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

    def test_state_can_be_updated(self) -> None:
        """State dict can be mutated."""
        ctx = _make_context()
        ctx.state["key"] = "value"
        assert ctx.state["key"] == "value"
