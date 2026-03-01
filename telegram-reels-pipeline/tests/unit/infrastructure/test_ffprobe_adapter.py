"""Tests for FfprobeAdapter — success, non-zero exit, invalid output, OSError, timeout."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.infrastructure.adapters.ffprobe_adapter import FfprobeAdapter

# --- Helpers ---


def _make_process_mock(
    returncode: int = 0,
    stdout: bytes = b"12.345\n",
) -> MagicMock:
    """Create a mock subprocess that returns the given stdout and returncode."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    return proc


# --- Tests ---


class TestFfprobeAdapterSuccess:
    """Verify successful duration probing."""

    @pytest.mark.asyncio
    async def test_returns_duration(self, tmp_path: Path) -> None:
        """Returns parsed float duration from ffprobe stdout."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            proc = _make_process_mock(returncode=0, stdout=b"42.5\n")
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.wait_for = AsyncMock(return_value=(b"42.5\n", b""))

            result = await adapter.probe(clip)

        assert result == 42.5

    @pytest.mark.asyncio
    async def test_returns_integer_duration(self, tmp_path: Path) -> None:
        """Returns duration when ffprobe returns an integer-like value."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            proc = _make_process_mock(returncode=0, stdout=b"60\n")
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.wait_for = AsyncMock(return_value=(b"60\n", b""))

            result = await adapter.probe(clip)

        assert result == 60.0


class TestFfprobeAdapterFailures:
    """Verify graceful failure handling."""

    @pytest.mark.asyncio
    async def test_non_zero_exit_returns_none(self, tmp_path: Path) -> None:
        """Non-zero exit code returns None."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            proc = _make_process_mock(returncode=1, stdout=b"")
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.wait_for = AsyncMock(return_value=(b"", b""))

            result = await adapter.probe(clip)

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_output_returns_none(self, tmp_path: Path) -> None:
        """Non-numeric stdout returns None (ValueError caught)."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            proc = _make_process_mock(returncode=0, stdout=b"N/A\n")
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.wait_for = AsyncMock(return_value=(b"N/A\n", b""))

            result = await adapter.probe(clip)

        assert result is None

    @pytest.mark.asyncio
    async def test_oserror_returns_none(self, tmp_path: Path) -> None:
        """OSError (e.g., ffprobe not found) returns None."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(side_effect=OSError("not found"))
            mock_asyncio.subprocess = asyncio.subprocess

            result = await adapter.probe(clip)

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, tmp_path: Path) -> None:
        """Timeout returns None."""
        clip = tmp_path / "video.mp4"
        clip.touch()
        adapter = FfprobeAdapter()

        with patch("pipeline.infrastructure.adapters.ffprobe_adapter.asyncio") as mock_asyncio:
            proc = _make_process_mock()
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = asyncio.subprocess
            mock_asyncio.wait_for = AsyncMock(side_effect=TimeoutError)

            result = await adapter.probe(clip)

        assert result is None
