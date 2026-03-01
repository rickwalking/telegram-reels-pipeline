"""Tests for SetupWorkspaceCommand — workspace creation, resume, and preflight."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.application.cli.commands.setup_workspace import (
    SetupWorkspaceCommand,
    print_resume_preflight,
)
from pipeline.application.cli.context import PipelineContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# print_resume_preflight
# ---------------------------------------------------------------------------


class TestPrintResumePreflight:
    def test_prints_artifact_status(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "research-output.json").write_text("{}")
        print_resume_preflight(tmp_path, start_stage=3)
        out = capsys.readouterr().out
        assert "Stage 1 (router): ok" in out
        assert "Stage 2 (research): ok" in out
        assert "Stage 3 (transcript): missing" in out
        assert ">>" in out  # marker for start stage

    def test_empty_workspace(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        print_resume_preflight(tmp_path, start_stage=1)
        out = capsys.readouterr().out
        assert "Stage 1 (router): missing" in out


# ---------------------------------------------------------------------------
# SetupWorkspaceCommand — new workspace creation
# ---------------------------------------------------------------------------


class TestSetupWorkspaceCommandNew:
    def test_creates_new_workspace(self, tmp_path: Path) -> None:
        ctx = _make_context()
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.workspace is not None
        assert ctx.workspace.is_dir()
        assert result.data.get("resumed") is False

    def test_workspace_under_runs_dir(self, tmp_path: Path) -> None:
        ctx = _make_context()
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        asyncio.run(cmd.execute(ctx))
        assert ctx.workspace is not None
        assert "runs" in str(ctx.workspace)

    def test_name_property(self, tmp_path: Path) -> None:
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        assert cmd.name == "setup-workspace"


# ---------------------------------------------------------------------------
# SetupWorkspaceCommand — resume existing workspace
# ---------------------------------------------------------------------------


class TestSetupWorkspaceCommandResume:
    def test_resume_sets_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "existing-workspace"
        workspace.mkdir()
        ctx = _make_context(resume_workspace=str(workspace))
        ctx.state.start_stage = 1
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.workspace == workspace
        assert result.data.get("resumed") is True

    def test_resume_with_artifacts(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "router-output.json").write_text("{}")
        (workspace / "research-output.json").write_text("{}")
        ctx = _make_context(resume_workspace=str(workspace))
        ctx.state.start_stage = 3
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert len(ctx.artifacts) == 2

    def test_resume_start_stage_1_no_artifacts_loaded(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "router-output.json").write_text("{}")
        ctx = _make_context(resume_workspace=str(workspace))
        ctx.state.start_stage = 1
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        asyncio.run(cmd.execute(ctx))
        # start_stage == 1 means no artifact loading
        assert ctx.artifacts == ()

    def test_resume_missing_dir_fails(self, tmp_path: Path) -> None:
        ctx = _make_context(resume_workspace=str(tmp_path / "nonexistent"))
        ctx.state.start_stage = 1
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "not a valid directory" in result.message

    def test_workspace_path_set_on_context(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        ctx = _make_context(resume_workspace=str(workspace))
        ctx.state.start_stage = 1
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        asyncio.run(cmd.execute(ctx))
        assert ctx.workspace == workspace
        assert ctx.has_workspace is True

    def test_resume_prints_preflight(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "router-output.json").write_text("{}")
        ctx = _make_context(resume_workspace=str(workspace))
        ctx.state.start_stage = 2
        cmd = SetupWorkspaceCommand(workspace_base=tmp_path)
        asyncio.run(cmd.execute(ctx))
        out = capsys.readouterr().out
        assert "Workspace artifact check:" in out
        assert "Stage 1 (router): ok" in out
