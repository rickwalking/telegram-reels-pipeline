"""Tests for RecoveryChain — multi-level error recovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from pipeline.application.recovery_chain import (
    RECOVERY_ORDER,
    RecoveryChain,
    RecoveryLevel,
    RecoveryResult,
)
from pipeline.domain.enums import PipelineStage
from pipeline.domain.errors import AgentExecutionError
from pipeline.domain.models import AgentRequest, AgentResult


def _make_request(tmp_path: Path) -> AgentRequest:
    step = tmp_path / "step.md"
    step.write_text("step content")
    agent = tmp_path / "agent.md"
    agent.write_text("agent content")
    return AgentRequest(stage=PipelineStage.ROUTER, step_file=step, agent_definition=agent)


def _make_result() -> AgentResult:
    return AgentResult(status="completed", duration_seconds=1.0)


class TestRecoveryChainRetry:
    async def test_retry_succeeds(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_result()
        chain = RecoveryChain(agent_port)

        result = await chain.recover(_make_request(tmp_path), RuntimeError("test"))

        assert result.success
        assert result.level == RecoveryLevel.RETRY
        assert result.result is not None

    async def test_retry_fails_proceeds_to_fork(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = [
            AgentExecutionError("retry failed"),  # L1 retry fails
            _make_result(),  # L2 fork succeeds
        ]
        chain = RecoveryChain(agent_port)

        result = await chain.recover(_make_request(tmp_path), RuntimeError("test"))

        assert result.success
        assert result.level == RecoveryLevel.FORK


class TestRecoveryChainFork:
    async def test_fork_strips_attempt_history(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = [
            AgentExecutionError("retry failed"),  # L1 retry fails
            _make_result(),  # L2 fork succeeds
        ]
        chain = RecoveryChain(agent_port)
        step = tmp_path / "step.md"
        step.write_text("step")
        agent = tmp_path / "agent.md"
        agent.write_text("agent")
        request = AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=step,
            agent_definition=agent,
            attempt_history=({"attempt": "1", "score": "50"},),
        )

        result = await chain.recover(request, RuntimeError("test"))

        assert result.success
        assert result.level == RecoveryLevel.FORK
        fork_call = agent_port.execute.call_args_list[1][0][0]
        assert fork_call.attempt_history == ()
        assert fork_call.prior_artifacts == request.prior_artifacts


class TestRecoveryChainFresh:
    async def test_fresh_strips_prior_artifacts(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = [
            AgentExecutionError("retry"),
            AgentExecutionError("fork"),
            _make_result(),  # L3 fresh succeeds
        ]
        chain = RecoveryChain(agent_port)
        request = _make_request(tmp_path)

        result = await chain.recover(request, RuntimeError("test"))

        assert result.success
        assert result.level == RecoveryLevel.FRESH
        # Fresh request should have been called with no prior_artifacts
        fresh_call = agent_port.execute.call_args_list[2][0][0]
        assert fresh_call.prior_artifacts == ()
        assert fresh_call.attempt_history == ()


class TestRecoveryChainEscalate:
    async def test_escalates_after_all_fail(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = AgentExecutionError("always fails")
        messaging = AsyncMock()
        chain = RecoveryChain(agent_port, messaging_port=messaging)

        result = await chain.recover(_make_request(tmp_path), RuntimeError("test"))

        assert not result.success
        assert result.level == RecoveryLevel.ESCALATE
        assert "Pipeline needs help" in result.escalation_message
        messaging.notify_user.assert_called_once()

    async def test_escalates_without_messaging(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = AgentExecutionError("always fails")
        chain = RecoveryChain(agent_port, messaging_port=None)

        result = await chain.recover(_make_request(tmp_path), RuntimeError("test"))

        assert not result.success
        assert result.level == RecoveryLevel.ESCALATE

    async def test_escalation_swallows_notification_error(self, tmp_path: Path) -> None:
        agent_port = AsyncMock()
        agent_port.execute.side_effect = AgentExecutionError("always fails")
        messaging = AsyncMock()
        messaging.notify_user.side_effect = RuntimeError("telegram down")
        chain = RecoveryChain(agent_port, messaging_port=messaging)

        result = await chain.recover(_make_request(tmp_path), RuntimeError("test"))

        assert not result.success
        assert result.level == RecoveryLevel.ESCALATE


class TestRecoveryResult:
    def test_success_result(self) -> None:
        result = RecoveryResult(success=True, level=RecoveryLevel.RETRY, result=_make_result())
        assert result.success
        assert result.escalation_message == ""

    def test_escalation_result(self) -> None:
        result = RecoveryResult(success=False, level=RecoveryLevel.ESCALATE, escalation_message="help")
        assert not result.success
        assert result.result is None


class TestRecoveryOrder:
    def test_order_length(self) -> None:
        assert len(RECOVERY_ORDER) == 4

    def test_order_starts_with_retry(self) -> None:
        assert RECOVERY_ORDER[0] == RecoveryLevel.RETRY

    def test_order_ends_with_escalate(self) -> None:
        assert RECOVERY_ORDER[-1] == RecoveryLevel.ESCALATE
