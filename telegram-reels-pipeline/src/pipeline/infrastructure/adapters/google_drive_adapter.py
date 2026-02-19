"""GoogleDriveAdapter — FileDeliveryPort implementation for large file uploads."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pipeline.domain.errors import ConfigurationError, PipelineError

logger = logging.getLogger(__name__)


class GoogleDriveUploadError(PipelineError):
    """Failed to upload file to Google Drive."""


class GoogleDriveAdapter:
    """Upload files to Google Drive using a service account.

    Implements FileDeliveryPort. The Google API client libraries are imported
    lazily — if they are not installed, upload() raises ConfigurationError.
    All blocking I/O is offloaded via asyncio.to_thread.
    """

    def __init__(self, credentials_path: Path, folder_id: str = "") -> None:
        self._credentials_path = credentials_path
        self._folder_id = folder_id

    async def upload(self, path: Path) -> str:
        """Upload a file to Google Drive and return a shareable link.

        Raises ConfigurationError if google-api-python-client is not installed.
        Raises GoogleDriveUploadError on upload failure.
        """
        exists = await asyncio.to_thread(path.exists)
        if not exists:
            raise GoogleDriveUploadError(f"File not found: {path}")

        return await asyncio.to_thread(self._upload_sync, path)

    def _upload_sync(self, path: Path) -> str:
        """Synchronous upload — runs in a thread."""
        try:
            from google.oauth2.service_account import Credentials  # type: ignore[import-not-found]
            from googleapiclient.discovery import build  # type: ignore[import-not-found]
            from googleapiclient.http import MediaFileUpload  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ConfigurationError(
                "google-api-python-client and google-auth are required for Google Drive uploads. "
                "Install with: pip install google-api-python-client google-auth"
            ) from exc

        try:
            scopes = ["https://www.googleapis.com/auth/drive.file"]
            creds = Credentials.from_service_account_file(str(self._credentials_path), scopes=scopes)
            service = build("drive", "v3", credentials=creds)

            file_metadata: dict[str, object] = {"name": path.name}
            if self._folder_id:
                file_metadata["parents"] = [self._folder_id]

            media = MediaFileUpload(str(path), resumable=True)
            file_result = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            file_id = file_result["id"]

            # Make the file viewable by anyone with the link
            service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

            link = f"https://drive.google.com/file/d/{file_id}/view"
            logger.info("Uploaded %s to Google Drive: %s", path.name, link)
            return link

        except Exception as exc:
            raise GoogleDriveUploadError(f"Failed to upload {path.name}: {exc}") from exc
