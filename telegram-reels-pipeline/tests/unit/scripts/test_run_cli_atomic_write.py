"""Tests for run_cli.py — atomic write failure handling in _download_cutaway_clips."""

# ruff: noqa: E402, I001

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add scripts parent so we can import run_cli
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))
import run_cli  # noqa: F401


class TestDownloadCutawayClipsAtomicWrite:
    """Verify atomic write in _download_cutaway_clips cleans up on failure."""

    async def test_os_replace_failure_cleans_temp(self, tmp_path: Path) -> None:
        """When os.replace raises, temp file is cleaned up and exception re-raised."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        # Mock ExternalClipDownloader
        mock_downloader = AsyncMock()
        downloaded_file = workspace / "external_clips" / "raw.mp4"
        downloaded_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_file.write_bytes(b"video")
        mock_downloader.download = AsyncMock(return_value=downloaded_file)

        with (
            patch("run_cli.ExternalClipDownloader", return_value=mock_downloader),
            patch("run_cli._parse_cutaway_spec", return_value=("https://example.com/vid", 10.0)),
            patch("run_cli._probe_clip_duration", new_callable=AsyncMock, return_value=5.0),
            patch("run_cli.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            await run_cli._download_cutaway_clips(["https://example.com/vid@10.0"], workspace)

        # No temp files left behind
        tmp_files = list(workspace.glob("*.tmp"))
        assert tmp_files == []

    async def test_successful_write(self, tmp_path: Path) -> None:
        """Normal case: external-clips.json written atomically."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        mock_downloader = AsyncMock()
        downloaded_file = workspace / "external_clips" / "raw.mp4"
        downloaded_file.parent.mkdir(parents=True, exist_ok=True)
        downloaded_file.write_bytes(b"video")
        mock_downloader.download = AsyncMock(return_value=downloaded_file)

        with (
            patch("run_cli.ExternalClipDownloader", return_value=mock_downloader),
            patch("run_cli._parse_cutaway_spec", return_value=("https://example.com/vid", 10.0)),
            patch("run_cli._probe_clip_duration", new_callable=AsyncMock, return_value=5.0),
        ):
            manifest = await run_cli._download_cutaway_clips(["https://example.com/vid@10.0"], workspace)

        assert len(manifest) == 1
        manifest_path = workspace / "external-clips.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert len(data) == 1

        # No temp files left behind
        tmp_files = list(workspace.glob("*.tmp"))
        assert tmp_files == []
