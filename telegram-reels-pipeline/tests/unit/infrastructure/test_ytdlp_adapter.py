"""Tests for YtDlpAdapter — VideoDownloadPort via yt-dlp subprocess."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.domain.ports import VideoDownloadPort
from pipeline.infrastructure.adapters.ytdlp_adapter import (
    MAX_RETRIES,
    YtDlpAdapter,
    YtDlpError,
    _parse_metadata,
)


def _make_metadata_json(
    title: str = "Test Episode",
    duration: float = 3600.0,
    channel: str = "TestChannel",
    upload_date: str = "20260201",
    description: str = "A test episode about AI.",
) -> str:
    return json.dumps(
        {
            "title": title,
            "duration": duration,
            "channel": channel,
            "upload_date": upload_date,
            "description": description,
        }
    )


def _make_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(
        return_value=(stdout.encode(), stderr.encode())
    )
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    return proc


class TestDownloadMetadata:
    async def test_parses_metadata_from_json(self) -> None:
        adapter = YtDlpAdapter()
        meta_json = _make_metadata_json()
        proc = _make_proc(stdout=meta_json)

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()

            result = await adapter.download_metadata("https://youtu.be/test")

        assert result.title == "Test Episode"
        assert result.duration_seconds == 3600.0
        assert result.channel == "TestChannel"
        assert result.url == "https://youtu.be/test"

    async def test_raises_on_nonzero_exit(self) -> None:
        adapter = YtDlpAdapter()
        proc = _make_proc(returncode=1, stderr="ERROR: Video unavailable")

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()
            mock_asyncio.sleep = AsyncMock()

            with pytest.raises(YtDlpError, match="failed after"):
                await adapter.download_metadata("https://youtu.be/test")


class TestRetryLogic:
    async def test_retries_on_failure(self) -> None:
        adapter = YtDlpAdapter()
        fail_proc = _make_proc(returncode=1, stderr="network error")
        ok_proc = _make_proc(stdout=_make_metadata_json())

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(side_effect=[fail_proc, ok_proc])
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()
            mock_asyncio.sleep = AsyncMock()

            result = await adapter.download_metadata("https://youtu.be/test")
            assert result.title == "Test Episode"
            assert mock_asyncio.sleep.call_count == 1

    async def test_exponential_backoff_timing(self) -> None:
        adapter = YtDlpAdapter()
        fail_proc = _make_proc(returncode=1, stderr="error")
        ok_proc = _make_proc(stdout=_make_metadata_json())

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(
                side_effect=[fail_proc, fail_proc, ok_proc]
            )
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()
            mock_asyncio.sleep = AsyncMock()

            await adapter.download_metadata("https://youtu.be/test")
            # Backoffs: 1s, 2s
            backoff_args = [call.args[0] for call in mock_asyncio.sleep.call_args_list]
            assert backoff_args == [1.0, 2.0]

    async def test_exhausts_retries(self) -> None:
        adapter = YtDlpAdapter()
        fail_proc = _make_proc(returncode=1, stderr="persistent error")

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(
                return_value=fail_proc,
            )
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()
            mock_asyncio.sleep = AsyncMock()

            with pytest.raises(YtDlpError, match=f"failed after {MAX_RETRIES}"):
                await adapter.download_metadata("https://youtu.be/test")


class TestDownloadSubtitles:
    async def test_returns_subtitle_path(self, tmp_path: Path) -> None:
        adapter = YtDlpAdapter()
        output = tmp_path / "subs.srt"
        # Simulate yt-dlp creating the file
        expected = tmp_path / "subs.en.srt"
        expected.write_text("1\n00:00:00,000 --> 00:00:05,000\nHello\n")

        proc = _make_proc(stdout="")

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()

            result = await adapter.download_subtitles("https://youtu.be/test", output)
            assert result == expected

    async def test_raises_when_no_subtitle_file(self, tmp_path: Path) -> None:
        adapter = YtDlpAdapter()
        output = tmp_path / "subs.srt"
        proc = _make_proc(stdout="")

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()
            mock_asyncio.sleep = AsyncMock()

            with pytest.raises(YtDlpError, match="Subtitle file not found"):
                await adapter.download_subtitles("https://youtu.be/test", output)


class TestDownloadVideo:
    async def test_returns_video_path(self, tmp_path: Path) -> None:
        adapter = YtDlpAdapter()
        output = tmp_path / "video.mp4"
        output.write_bytes(b"fake-video-data")
        proc = _make_proc(stdout="")

        with patch("pipeline.infrastructure.adapters.ytdlp_adapter.asyncio") as mock_asyncio:
            mock_asyncio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_asyncio.subprocess = MagicMock()
            mock_asyncio.subprocess.PIPE = -1
            mock_asyncio.timeout = lambda s: _FakeTimeout()

            result = await adapter.download_video("https://youtu.be/test", output)
            assert result == output


class TestParseMetadata:
    def test_parses_valid_json(self) -> None:
        raw = _make_metadata_json(title="My Podcast", duration=7200.0)
        result = _parse_metadata(raw, "https://youtu.be/test")
        assert result.title == "My Podcast"
        assert result.duration_seconds == 7200.0

    def test_uses_uploader_when_channel_missing(self) -> None:
        raw = json.dumps({"title": "Test", "duration": 60, "uploader": "Uploader1"})
        result = _parse_metadata(raw, "https://youtu.be/test")
        assert result.channel == "Uploader1"

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(YtDlpError, match="parse"):
            _parse_metadata("not-json", "https://youtu.be/test")

    def test_raises_on_zero_duration(self) -> None:
        raw = json.dumps({"title": "Test", "duration": 0})
        with pytest.raises(YtDlpError, match="Invalid metadata"):
            _parse_metadata(raw, "https://youtu.be/test")


class TestProtocol:
    def test_satisfies_video_download_port(self) -> None:
        adapter = YtDlpAdapter()
        assert isinstance(adapter, VideoDownloadPort)


class _FakeTimeout:
    """Fake async context manager for asyncio.timeout."""

    async def __aenter__(self) -> _FakeTimeout:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass
