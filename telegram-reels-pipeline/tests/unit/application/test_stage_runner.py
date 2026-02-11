"""Tests for StageRunner — stage execution through QA and recovery."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.stage_runner import StageRunner
from pipeline.domain.enums import PipelineStage, QADecision
from pipeline.domain.models import AgentRequest, QACritique, ReflectionResult
from pipeline.domain.types import GateName

_GATE = GateName("router")
_GATE_CRITERIA = "Test criteria for QA evaluation"


def _make_request() -> AgentRequest:
    return AgentRequest(
        stage=PipelineStage.ROUTER,
        step_file=Path("/tmp/step.md"),
        agent_definition=Path("/tmp/agent.md"),
    )


def _make_reflection_result(decision: QADecision = QADecision.PASS, score: int = 85) -> ReflectionResult:
    return ReflectionResult(
        best_critique=QACritique(
            decision=decision,
            score=score,
            gate=_GATE,
            attempt=1,
            confidence=0.9,
        ),
        artifacts=(Path("/tmp/output.md"),),
        attempts=1,
    )


def _make_runner(
    reflection_result: ReflectionResult | None = None,
    reflection_error: Exception | None = None,
    recovery_error: Exception | None = None,
) -> tuple[StageRunner, MagicMock, MagicMock, MagicMock]:
    reflection_loop = MagicMock()
    if reflection_error:
        reflection_loop.run = AsyncMock(side_effect=reflection_error)
    else:
        reflection_loop.run = AsyncMock(return_value=reflection_result or _make_reflection_result())

    recovery_chain = MagicMock()
    if recovery_error:
        recovery_chain.recover = AsyncMock(side_effect=recovery_error)
    else:
        recovery_result = MagicMock()
        recovery_result.level.value = "retry"
        recovery_chain.recover = AsyncMock(return_value=recovery_result)

    event_bus = MagicMock()
    event_bus.publish = AsyncMock()

    runner = StageRunner(
        reflection_loop=reflection_loop,
        recovery_chain=recovery_chain,
        event_bus=event_bus,
    )
    return runner, reflection_loop, recovery_chain, event_bus


class TestStageRunnerSuccess:
    async def test_returns_reflection_result(self) -> None:
        expected = _make_reflection_result()
        runner, _, _, _ = _make_runner(reflection_result=expected)
        result = await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        assert result is expected

    async def test_emits_stage_entered_event(self) -> None:
        runner, _, _, event_bus = _make_runner()
        await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        events = [call.args[0] for call in event_bus.publish.call_args_list]
        assert any(e.event_name == "pipeline.stage_entered" for e in events)

    async def test_emits_stage_completed_event(self) -> None:
        runner, _, _, event_bus = _make_runner()
        await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        events = [call.args[0] for call in event_bus.publish.call_args_list]
        assert any(e.event_name == "pipeline.stage_completed" for e in events)

    async def test_completed_event_includes_score(self) -> None:
        result = _make_reflection_result(score=92)
        runner, _, _, event_bus = _make_runner(reflection_result=result)
        await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        events = [call.args[0] for call in event_bus.publish.call_args_list]
        completed = next(e for e in events if e.event_name == "pipeline.stage_completed")
        assert completed.data["score"] == 92

    async def test_passes_gate_to_reflection_loop(self) -> None:
        runner, reflection_loop, _, _ = _make_runner()
        await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        reflection_loop.run.assert_awaited_once()
        call_args = reflection_loop.run.call_args
        assert call_args.args[1] == _GATE
        assert call_args.args[2] == _GATE_CRITERIA


class TestStageRunnerRecovery:
    async def test_recovery_retries_reflection(self) -> None:
        reflection_loop = MagicMock()
        success = _make_reflection_result()
        reflection_loop.run = AsyncMock(side_effect=[RuntimeError("agent crash"), success])

        recovery_result = MagicMock()
        recovery_result.level.value = "retry"
        recovery_chain = MagicMock()
        recovery_chain.recover = AsyncMock(return_value=recovery_result)

        event_bus = MagicMock()
        event_bus.publish = AsyncMock()

        runner = StageRunner(
            reflection_loop=reflection_loop,
            recovery_chain=recovery_chain,
            event_bus=event_bus,
        )
        result = await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        assert result is success
        assert reflection_loop.run.call_count == 2

    async def test_unrecoverable_failure_raises(self) -> None:
        runner, _, _, _ = _make_runner(
            reflection_error=RuntimeError("crash"),
            recovery_error=RuntimeError("unrecoverable"),
        )
        with pytest.raises(RuntimeError, match="unrecoverable"):
            await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)

    async def test_failure_emits_run_failed_event(self) -> None:
        runner, _, _, event_bus = _make_runner(
            reflection_error=RuntimeError("crash"),
            recovery_error=RuntimeError("unrecoverable"),
        )
        with pytest.raises(RuntimeError):
            await runner.run_stage(_make_request(), _GATE, _GATE_CRITERIA)
        events = [call.args[0] for call in event_bus.publish.call_args_list]
        assert any(e.event_name == "pipeline.run_failed" for e in events)
