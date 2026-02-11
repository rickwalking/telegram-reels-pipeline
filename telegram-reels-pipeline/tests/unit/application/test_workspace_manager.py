"""Tests for WorkspaceManager — per-run workspace isolation."""

from __future__ import annotations

from pathlib import Path

from pipeline.application.workspace_manager import WorkspaceManager


class TestWorkspaceManagerCreate:
    def test_creates_workspace_directory(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        workspace = manager.create_workspace()
        assert workspace.is_dir()

    def test_creates_assets_subdirectory(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        workspace = manager.create_workspace()
        assert (workspace / "assets").is_dir()

    def test_workspace_under_runs_dir(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        workspace = manager.create_workspace()
        assert workspace.parent.name == "runs"

    def test_workspace_name_has_timestamp_and_id(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        workspace = manager.create_workspace()
        parts = workspace.name.split("-")
        assert len(parts) >= 2  # timestamp-shortid

    def test_creates_unique_workspaces(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        ws1 = manager.create_workspace()
        ws2 = manager.create_workspace()
        assert ws1 != ws2

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "deep" / "nested" / "workspace")
        workspace = manager.create_workspace()
        assert workspace.is_dir()


class TestWorkspaceManagerManagedContext:
    async def test_yields_workspace_path(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        async with manager.managed_workspace() as workspace:
            assert workspace.is_dir()

    async def test_workspace_persists_after_exit(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        async with manager.managed_workspace() as workspace:
            path = workspace
        assert path.is_dir()  # Still exists after context exit

    async def test_workspace_persists_after_error(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        workspace_path: Path | None = None
        try:
            async with manager.managed_workspace() as workspace:
                workspace_path = workspace
                raise RuntimeError("simulated crash")
        except RuntimeError:
            pass
        assert workspace_path is not None
        assert workspace_path.is_dir()


class TestWorkspaceManagerList:
    def test_list_empty(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        assert manager.list_workspaces() == []

    def test_list_returns_created_workspaces(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        manager.create_workspace()
        manager.create_workspace()
        listed = manager.list_workspaces()
        assert len(listed) == 2

    def test_list_sorted_chronologically(self, tmp_path: Path) -> None:
        manager = WorkspaceManager(tmp_path / "workspace")
        manager.create_workspace()
        manager.create_workspace()
        listed = manager.list_workspaces()
        assert listed[0].name <= listed[1].name
