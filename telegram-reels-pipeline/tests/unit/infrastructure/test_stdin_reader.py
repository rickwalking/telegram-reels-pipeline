"""Tests for StdinReader — normal input, EOF, KeyboardInterrupt, timeout."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pipeline.infrastructure.adapters.stdin_reader import StdinReader


class TestStdinReaderSuccess:
    """Verify successful input reading."""

    @pytest.mark.asyncio
    async def test_returns_stripped_input(self) -> None:
        """Normal input is stripped and returned."""
        reader = StdinReader()

        with patch(
            "pipeline.infrastructure.adapters.stdin_reader.asyncio.wait_for",
            new_callable=AsyncMock,
            return_value="  hello world  ",
        ):
            result = await reader.read("Enter: ", timeout=30)

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_returns_empty_string(self) -> None:
        """Empty input (just whitespace) returns empty string."""
        reader = StdinReader()

        with patch(
            "pipeline.infrastructure.adapters.stdin_reader.asyncio.wait_for",
            new_callable=AsyncMock,
            return_value="   ",
        ):
            result = await reader.read("Enter: ", timeout=30)

        assert result == ""


class TestStdinReaderFailures:
    """Verify graceful failure handling."""

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self) -> None:
        """TimeoutError returns None."""
        reader = StdinReader()

        with patch(
            "pipeline.infrastructure.adapters.stdin_reader.asyncio.wait_for",
            new_callable=AsyncMock,
            side_effect=TimeoutError,
        ):
            result = await reader.read("Enter: ", timeout=1)

        assert result is None

    @pytest.mark.asyncio
    async def test_eof_returns_none(self) -> None:
        """EOFError returns None."""
        reader = StdinReader()

        with patch(
            "pipeline.infrastructure.adapters.stdin_reader.asyncio.wait_for",
            new_callable=AsyncMock,
            side_effect=EOFError,
        ):
            result = await reader.read("Enter: ", timeout=30)

        assert result is None

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_returns_none(self) -> None:
        """KeyboardInterrupt returns None."""
        reader = StdinReader()

        with patch(
            "pipeline.infrastructure.adapters.stdin_reader.asyncio.wait_for",
            new_callable=AsyncMock,
            side_effect=KeyboardInterrupt,
        ):
            result = await reader.read("Enter: ", timeout=30)

        assert result is None
