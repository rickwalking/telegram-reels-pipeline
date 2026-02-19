"""Tests for GoogleDriveAdapter — Google Drive file upload."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from pipeline.domain.errors import ConfigurationError
from pipeline.infrastructure.adapters.google_drive_adapter import (
    GoogleDriveAdapter,
    GoogleDriveUploadError,
)


def _inject_google_mocks() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Inject fake google modules into sys.modules and return (Credentials, build, MediaFileUpload)."""
    mock_creds_cls = MagicMock()
    mock_build_fn = MagicMock()
    mock_media_cls = MagicMock()

    # Build module hierarchy
    google_mod = ModuleType("google")
    google_oauth2 = ModuleType("google.oauth2")
    google_oauth2_sa = ModuleType("google.oauth2.service_account")
    google_oauth2_sa.Credentials = mock_creds_cls  # type: ignore[attr-defined]

    googleapiclient = ModuleType("googleapiclient")
    googleapiclient_discovery = ModuleType("googleapiclient.discovery")
    googleapiclient_discovery.build = mock_build_fn  # type: ignore[attr-defined]
    googleapiclient_http = ModuleType("googleapiclient.http")
    googleapiclient_http.MediaFileUpload = mock_media_cls  # type: ignore[attr-defined]

    modules = {
        "google": google_mod,
        "google.oauth2": google_oauth2,
        "google.oauth2.service_account": google_oauth2_sa,
        "googleapiclient": googleapiclient,
        "googleapiclient.discovery": googleapiclient_discovery,
        "googleapiclient.http": googleapiclient_http,
    }

    return mock_creds_cls, mock_build_fn, mock_media_cls, modules  # type: ignore[return-value]


class TestGoogleDriveAdapter:
    async def test_missing_file_raises(self, tmp_path: Path) -> None:
        adapter = GoogleDriveAdapter(credentials_path=tmp_path / "creds.json")
        with pytest.raises(GoogleDriveUploadError, match="File not found"):
            await adapter.upload(tmp_path / "nonexistent.mp4")

    async def test_missing_google_libs_raises_configuration_error(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(credentials_path=tmp_path / "creds.json")

        # Block all google imports
        with (
            patch.dict(
                sys.modules,
                {
                    "google": None,
                    "google.oauth2": None,
                    "google.oauth2.service_account": None,
                    "googleapiclient": None,
                    "googleapiclient.discovery": None,
                    "googleapiclient.http": None,
                },
            ),
            pytest.raises(ConfigurationError, match="google-api-python-client"),
        ):
            await adapter.upload(video)

    async def test_successful_upload_returns_link(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(
            credentials_path=tmp_path / "creds.json",
            folder_id="folder123",
        )

        with patch.object(
            GoogleDriveAdapter,
            "_upload_sync",
            return_value="https://drive.google.com/file/d/file_abc/view",
        ):
            link = await adapter.upload(video)

        assert link == "https://drive.google.com/file/d/file_abc/view"

    def test_upload_sync_sets_folder_parent(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(
            credentials_path=tmp_path / "creds.json",
            folder_id="folder123",
        )

        mock_creds_cls, mock_build_fn, mock_media_cls, modules = _inject_google_mocks()

        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_service.files.return_value = mock_files
        mock_files.create.return_value.execute.return_value = {"id": "file_xyz"}
        mock_service.permissions.return_value.create.return_value.execute.return_value = {}

        mock_creds_cls.from_service_account_file.return_value = MagicMock()
        mock_build_fn.return_value = mock_service

        with patch.dict(sys.modules, modules):
            link = adapter._upload_sync(video)

        assert "file_xyz" in link
        create_call = mock_files.create.call_args
        body = create_call.kwargs.get("body", create_call[1].get("body", {}))
        assert body.get("parents") == ["folder123"]

    def test_upload_sync_no_folder(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(credentials_path=tmp_path / "creds.json")

        mock_creds_cls, mock_build_fn, _, modules = _inject_google_mocks()

        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_service.files.return_value = mock_files
        mock_files.create.return_value.execute.return_value = {"id": "file_nop"}
        mock_service.permissions.return_value.create.return_value.execute.return_value = {}

        mock_creds_cls.from_service_account_file.return_value = MagicMock()
        mock_build_fn.return_value = mock_service

        with patch.dict(sys.modules, modules):
            link = adapter._upload_sync(video)

        assert "file_nop" in link
        create_call = mock_files.create.call_args
        body = create_call.kwargs.get("body", create_call[1].get("body", {}))
        assert "parents" not in body

    def test_upload_sync_api_error_wraps(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(credentials_path=tmp_path / "creds.json")

        mock_creds_cls, mock_build_fn, _, modules = _inject_google_mocks()
        mock_creds_cls.from_service_account_file.return_value = MagicMock()
        mock_build_fn.side_effect = RuntimeError("API down")

        with patch.dict(sys.modules, modules), pytest.raises(GoogleDriveUploadError, match="Failed to upload"):
            adapter._upload_sync(video)

    def test_error_hierarchy(self) -> None:
        from pipeline.domain.errors import PipelineError

        assert issubclass(GoogleDriveUploadError, PipelineError)

    def test_exception_chaining_on_upload_error(self, tmp_path: Path) -> None:
        video = tmp_path / "reel.mp4"
        video.write_bytes(b"video-data")

        adapter = GoogleDriveAdapter(credentials_path=tmp_path / "creds.json")

        mock_creds_cls, mock_build_fn, _, modules = _inject_google_mocks()
        mock_creds_cls.from_service_account_file.return_value = MagicMock()
        mock_build_fn.side_effect = RuntimeError("API down")

        with patch.dict(sys.modules, modules), pytest.raises(GoogleDriveUploadError) as exc_info:
            adapter._upload_sync(video)

        assert exc_info.value.__cause__ is not None
