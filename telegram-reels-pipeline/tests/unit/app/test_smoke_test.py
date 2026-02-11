"""Tests for smoke_test module — connectivity checks with mocked externals."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.smoke_test import (
    CheckResult,
    check_claude_cli,
    check_ffmpeg,
    check_telegram,
    check_youtube,
)

_SUBPROCESS = "pipeline.smoke_test.asyncio.create_subprocess_exec"


def _mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


class TestCheckTelegram:
    async def test_missing_token(self) -> None:
        result = await check_telegram("", "12345")
        assert not result.passed
        assert "not set" in result.message

    async def test_missing_chat_id(self) -> None:
        result = await check_telegram("some-token", "")
        assert not result.passed
        assert "not set" in result.message

    async def test_successful_send(self) -> None:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        with patch("telegram.Bot", return_value=mock_bot):
            result = await check_telegram("token", "12345")
        assert result.passed
        assert "successfully" in result.message
        mock_bot.send_message.assert_awaited_once()

    async def test_send_failure(self) -> None:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
        with patch("telegram.Bot", return_value=mock_bot):
            result = await check_telegram("token", "12345")
        assert not result.passed
        assert "Network error" in result.message


class TestCheckClaudeCli:
    async def test_claude_found(self) -> None:
        proc = _mock_proc(stdout=b"claude 1.0.0\n")
        with patch(_SUBPROCESS, new_callable=AsyncMock, return_value=proc):
            result = await check_claude_cli()
        assert result.passed
        assert "1.0.0" in result.message

    async def test_claude_not_found(self) -> None:
        with patch(_SUBPROCESS, new_callable=AsyncMock, side_effect=FileNotFoundError):
            result = await check_claude_cli()
        assert not result.passed
        assert "not found" in result.message

    async def test_claude_bad_exit(self) -> None:
        proc = _mock_proc(returncode=1, stderr=b"error")
        with patch(_SUBPROCESS, new_callable=AsyncMock, return_value=proc):
            result = await check_claude_cli()
        assert not result.passed
        assert "Exit code 1" in result.message


class TestCheckYoutube:
    async def test_ytdlp_success(self) -> None:
        import json

        metadata = json.dumps({"title": "Me at the zoo", "duration": 19}).encode()
        proc = _mock_proc(stdout=metadata)
        with patch(_SUBPROCESS, new_callable=AsyncMock, return_value=proc):
            result = await check_youtube()
        assert result.passed
        assert "Me at the zoo" in result.message

    async def test_ytdlp_not_found(self) -> None:
        with patch(_SUBPROCESS, new_callable=AsyncMock, side_effect=FileNotFoundError):
            result = await check_youtube()
        assert not result.passed
        assert "not found" in result.message

    async def test_ytdlp_bad_exit(self) -> None:
        proc = _mock_proc(returncode=1, stderr=b"HTTP 403")
        with patch(_SUBPROCESS, new_callable=AsyncMock, return_value=proc):
            result = await check_youtube()
        assert not result.passed
        assert "Exit code 1" in result.message


class TestCheckFfmpeg:
    async def test_ffmpeg_found(self) -> None:
        proc = _mock_proc(stdout=b"ffmpeg version 6.1\n")
        with patch(_SUBPROCESS, new_callable=AsyncMock, return_value=proc):
            result = await check_ffmpeg()
        assert result.passed
        assert "ffmpeg version 6.1" in result.message

    async def test_ffmpeg_not_found(self) -> None:
        with patch(_SUBPROCESS, new_callable=AsyncMock, side_effect=FileNotFoundError):
            result = await check_ffmpeg()
        assert not result.passed
        assert "not found" in result.message


class TestCheckResult:
    def test_frozen(self) -> None:
        r = CheckResult(service="test", passed=True, message="ok")
        assert r.service == "test"
        assert r.passed is True
        assert r.message == "ok"
