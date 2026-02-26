"""Tests for clink QA dispatch fallback behaviour in CliBackend.dispatch()."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.domain.errors import AgentExecutionError
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    d = tmp_path / "workspace"
    d.mkdir()
    return d


@pytest.fixture
def backend(work_dir: Path) -> CliBackend:
    return CliBackend(work_dir=work_dir, qa_via_clink=True)


class TestClinkFallback:
    async def test_clink_valid_json_returns_without_sonnet_fallback(self, backend: CliBackend) -> None:
        """When clink returns valid JSON, dispatch returns it directly — no Sonnet call."""
        clink_response = '{"decision": "PASS", "score": 85}'

        with (
            patch.object(backend, "_dispatch_via_clink", new_callable=AsyncMock, return_value=clink_response) as clink,
            patch.object(backend, "_dispatch_direct", new_callable=AsyncMock) as direct,
        ):
            result = await backend.dispatch("qa_evaluator", "Evaluate this")

        assert result == clink_response
        clink.assert_awaited_once()
        direct.assert_not_awaited()

    async def test_clink_non_json_falls_back_to_sonnet(self, backend: CliBackend) -> None:
        """When clink returns text without '{', dispatch falls back to Sonnet."""
        sonnet_response = '{"decision": "REVISE", "score": 40}'

        with (
            patch.object(backend, "_dispatch_via_clink", new_callable=AsyncMock, return_value="No valid output"),
            patch.object(backend, "_dispatch_direct", new_callable=AsyncMock, return_value=sonnet_response) as direct,
        ):
            result = await backend.dispatch("qa_evaluator", "Evaluate this")

        assert result == sonnet_response
        direct.assert_awaited_once_with("qa_evaluator", "Evaluate this", backend.effective_work_dir, "sonnet")

    async def test_clink_exception_falls_back_to_sonnet(self, backend: CliBackend) -> None:
        """When clink raises AgentExecutionError, dispatch falls back to Sonnet."""
        sonnet_response = '{"decision": "PASS", "score": 70}'

        with (
            patch.object(backend, "_dispatch_via_clink", new_callable=AsyncMock, return_value=None),
            patch.object(backend, "_dispatch_direct", new_callable=AsyncMock, return_value=sonnet_response) as direct,
        ):
            result = await backend.dispatch("qa_evaluator", "Evaluate this")

        assert result == sonnet_response
        direct.assert_awaited_once()

    async def test_both_clink_and_sonnet_fail_raises(self, backend: CliBackend) -> None:
        """When both clink and Sonnet fail, AgentExecutionError propagates."""
        with (
            patch.object(backend, "_dispatch_via_clink", new_callable=AsyncMock, return_value=None),
            patch.object(
                backend,
                "_dispatch_direct",
                new_callable=AsyncMock,
                side_effect=AgentExecutionError("Sonnet failed"),
            ),
            pytest.raises(AgentExecutionError, match="Sonnet failed"),
        ):
            await backend.dispatch("qa_evaluator", "Evaluate this")
