"""Integration tests for LocalFileStorageAdapter — real filesystem I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.infrastructure.adapters.local_file_storage_adapter import LocalFileStorageAdapter


@pytest.fixture
def workspace_base(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def storage_adapter(workspace_base: Path) -> LocalFileStorageAdapter:
    return LocalFileStorageAdapter(workspace_base_directory=str(workspace_base))


PIPELINE_RUN_ID = "2026-03-16-abc123"
BINARY_CONTENT = b"\x00\x01\x02\x03binary-media-content"


class TestSaveBinaryAsset:
    async def test_save_binary_asset_creates_file_with_correct_content(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        asset_name = "final-reel.mp4"

        # Act
        asset_reference = await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, asset_name, BINARY_CONTENT)

        # Assert
        expected_file_path = workspace_base / "runs" / PIPELINE_RUN_ID / asset_name
        assert expected_file_path.exists()
        assert expected_file_path.read_bytes() == BINARY_CONTENT
        assert asset_reference == f"runs/{PIPELINE_RUN_ID}/{asset_name}"

    async def test_save_binary_asset_leaves_no_temporary_files(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        asset_name = "thumbnail.png"

        # Act
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, asset_name, BINARY_CONTENT)

        # Assert
        run_directory = workspace_base / "runs" / PIPELINE_RUN_ID
        temporary_files = list(run_directory.glob("*.tmp"))
        assert temporary_files == []

    async def test_save_binary_asset_creates_run_directory_automatically(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        new_run_id = "2026-03-16-newrun"

        # Act
        await storage_adapter.save_binary_asset(new_run_id, "clip.mp4", BINARY_CONTENT)

        # Assert
        assert (workspace_base / "runs" / new_run_id).is_dir()

    async def test_save_binary_asset_overwrites_existing_file(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        asset_name = "reel.mp4"
        updated_content = b"updated-binary-content"
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, asset_name, BINARY_CONTENT)

        # Act
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, asset_name, updated_content)

        # Assert
        file_path = workspace_base / "runs" / PIPELINE_RUN_ID / asset_name
        assert file_path.read_bytes() == updated_content

    async def test_save_binary_asset_rejects_path_traversal_in_run_id(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange
        malicious_run_id = "../outside-workspace"

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid pipeline_run_id"):
            await storage_adapter.save_binary_asset(malicious_run_id, "file.mp4", BINARY_CONTENT)

    async def test_save_binary_asset_rejects_path_traversal_in_asset_name(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange
        malicious_asset_name = "../escape.mp4"

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid asset_name"):
            await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, malicious_asset_name, BINARY_CONTENT)


class TestSaveBinaryAssetFromPath:
    async def test_save_binary_asset_from_path_copies_file_correctly(
        self,
        storage_adapter: LocalFileStorageAdapter,
        workspace_base: Path,
        tmp_path: Path,
    ) -> None:
        # Arrange
        source_file = tmp_path / "source.mp4"
        source_file.write_bytes(BINARY_CONTENT)

        # Act
        asset_reference = await storage_adapter.save_binary_asset_from_path(
            PIPELINE_RUN_ID, "copied-reel.mp4", str(source_file)
        )

        # Assert
        destination_path = workspace_base / "runs" / PIPELINE_RUN_ID / "copied-reel.mp4"
        assert destination_path.exists()
        assert destination_path.read_bytes() == BINARY_CONTENT
        assert asset_reference == f"runs/{PIPELINE_RUN_ID}/copied-reel.mp4"

    async def test_save_binary_asset_from_path_leaves_no_temporary_files(
        self,
        storage_adapter: LocalFileStorageAdapter,
        workspace_base: Path,
        tmp_path: Path,
    ) -> None:
        # Arrange
        source_file = tmp_path / "video.mp4"
        source_file.write_bytes(BINARY_CONTENT)

        # Act
        await storage_adapter.save_binary_asset_from_path(PIPELINE_RUN_ID, "video.mp4", str(source_file))

        # Assert
        run_directory = workspace_base / "runs" / PIPELINE_RUN_ID
        assert list(run_directory.glob("*.tmp")) == []

    async def test_save_binary_asset_from_path_does_not_modify_source(
        self,
        storage_adapter: LocalFileStorageAdapter,
        tmp_path: Path,
    ) -> None:
        # Arrange
        source_file = tmp_path / "original.mp4"
        source_file.write_bytes(BINARY_CONTENT)

        # Act
        await storage_adapter.save_binary_asset_from_path(PIPELINE_RUN_ID, "copy.mp4", str(source_file))

        # Assert
        assert source_file.exists()
        assert source_file.read_bytes() == BINARY_CONTENT


class TestGetAssetAbsolutePath:
    async def test_get_asset_absolute_path_returns_valid_path(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        asset_name = "reel.mp4"
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, asset_name, BINARY_CONTENT)

        # Act
        absolute_path_string = await storage_adapter.get_asset_absolute_path(PIPELINE_RUN_ID, asset_name)

        # Assert
        resolved_path = Path(absolute_path_string)
        assert resolved_path.is_absolute()
        assert resolved_path.exists()
        assert resolved_path.read_bytes() == BINARY_CONTENT

    async def test_get_asset_absolute_path_rejects_path_traversal_in_run_id(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange
        malicious_run_id = "../../etc"

        # Act / Assert
        with pytest.raises(ValueError):
            await storage_adapter.get_asset_absolute_path(malicious_run_id, "passwd")

    async def test_get_asset_absolute_path_rejects_absolute_asset_name(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange
        absolute_asset_name = "/etc/passwd"

        # Act / Assert
        with pytest.raises(ValueError, match="Invalid asset_name"):
            await storage_adapter.get_asset_absolute_path(PIPELINE_RUN_ID, absolute_asset_name)


class TestListRunAssets:
    async def test_list_run_assets_returns_correct_file_names(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "clip-1.mp4", BINARY_CONTENT)
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "clip-2.mp4", BINARY_CONTENT)
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "thumbnail.png", BINARY_CONTENT)

        # Act
        listed_asset_names = await storage_adapter.list_run_assets(PIPELINE_RUN_ID)

        # Assert
        assert set(listed_asset_names) == {"clip-1.mp4", "clip-2.mp4", "thumbnail.png"}

    async def test_list_run_assets_returns_empty_tuple_for_nonexistent_run(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange / Act
        listed_asset_names = await storage_adapter.list_run_assets("nonexistent-run-id")

        # Assert
        assert listed_asset_names == ()

    async def test_list_run_assets_excludes_subdirectories(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "reel.mp4", BINARY_CONTENT)
        subdirectory = workspace_base / "runs" / PIPELINE_RUN_ID / "frames"
        subdirectory.mkdir(parents=True, exist_ok=True)

        # Act
        listed_asset_names = await storage_adapter.list_run_assets(PIPELINE_RUN_ID)

        # Assert
        assert "frames" not in listed_asset_names
        assert "reel.mp4" in listed_asset_names


class TestDeleteRunAssets:
    async def test_delete_run_assets_removes_directory(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "reel.mp4", BINARY_CONTENT)
        run_directory = workspace_base / "runs" / PIPELINE_RUN_ID
        assert run_directory.exists()

        # Act
        await storage_adapter.delete_run_assets(PIPELINE_RUN_ID)

        # Assert
        assert not run_directory.exists()

    async def test_delete_run_assets_is_idempotent_for_nonexistent_run(
        self, storage_adapter: LocalFileStorageAdapter
    ) -> None:
        # Arrange / Act / Assert — should not raise
        await storage_adapter.delete_run_assets("nonexistent-run-id")

    async def test_delete_run_assets_does_not_affect_other_runs(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        other_run_id = "2026-03-16-other-run"
        await storage_adapter.save_binary_asset(PIPELINE_RUN_ID, "reel.mp4", BINARY_CONTENT)
        await storage_adapter.save_binary_asset(other_run_id, "reel.mp4", BINARY_CONTENT)

        # Act
        await storage_adapter.delete_run_assets(PIPELINE_RUN_ID)

        # Assert
        other_run_directory = workspace_base / "runs" / other_run_id
        assert other_run_directory.exists()
        assert (other_run_directory / "reel.mp4").exists()


class TestGuardPathTraversal:
    async def test_get_asset_absolute_path_raises_on_symlink_escape(
        self, workspace_base: Path, tmp_path: Path
    ) -> None:
        # Arrange — create a workspace whose "runs" directory symlinks outside the workspace
        narrow_workspace = tmp_path / "narrow"
        narrow_workspace.mkdir()
        outside_directory = tmp_path / "outside"
        outside_directory.mkdir()
        runs_symlink = narrow_workspace / "runs"
        runs_symlink.symlink_to(outside_directory)
        adapter = LocalFileStorageAdapter(workspace_base_directory=str(narrow_workspace))

        # Act / Assert — resolved path escapes workspace_base, guard must reject it
        with pytest.raises(ValueError, match="Path traversal detected"):
            await adapter.get_asset_absolute_path("run-id", "file.mp4")


class TestIsolatedRunDirectories:
    async def test_separate_runs_use_isolated_directories(
        self, storage_adapter: LocalFileStorageAdapter, workspace_base: Path
    ) -> None:
        # Arrange
        run_id_alpha = "2026-03-16-alpha"
        run_id_beta = "2026-03-16-beta"
        content_alpha = b"alpha-video-bytes"
        content_beta = b"beta-video-bytes"

        # Act
        await storage_adapter.save_binary_asset(run_id_alpha, "reel.mp4", content_alpha)
        await storage_adapter.save_binary_asset(run_id_beta, "reel.mp4", content_beta)

        # Assert — each run has its own isolated content
        path_alpha = workspace_base / "runs" / run_id_alpha / "reel.mp4"
        path_beta = workspace_base / "runs" / run_id_beta / "reel.mp4"
        assert path_alpha.read_bytes() == content_alpha
        assert path_beta.read_bytes() == content_beta
        assert path_alpha.read_bytes() != path_beta.read_bytes()
