"""Tests for RunStageCommand and stage helper functions."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.cli.commands.run_stage import (
    RunStageCommand,
    stage_name,
)
from pipeline.domain.enums import PipelineStage, QADecision
from pipeline.domain.models import QACritique, ReflectionResult
from pipeline.domain.types import GateName

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reflection_result(
    escalation_needed: bool = False,
    artifacts: tuple[Path, ...] = (),
    score: int = 80,
) -> ReflectionResult:
    """Create a real ReflectionResult for testing."""
    decision = QADecision.FAIL if escalation_needed else QADecision.PASS
    critique = QACritique(decision=decision, score=score, gate=GateName("test"), attempt=1)
    return ReflectionResult(
        best_critique=critique,
        artifacts=artifacts,
        attempts=1,
        escalation_needed=escalation_needed,
    )


def _make_mock_runner(result: ReflectionResult) -> MagicMock:
    """Create a mock StageRunner that returns a single result."""
    mock = MagicMock()
    mock.run_stage = AsyncMock(return_value=result)
    return mock


def _make_mock_runner_raises(exc: Exception) -> MagicMock:
    """Create a mock StageRunner that raises an exception."""
    mock = MagicMock()
    mock.run_stage = AsyncMock(side_effect=exc)
    return mock


class _StubHook:
    """Test stub for StageHook protocol."""

    def __init__(
        self,
        *,
        target_stage: PipelineStage | None = None,
        target_phase: Literal["pre", "post"] | None = None,
    ) -> None:
        self._target_stage = target_stage
        self._target_phase = target_phase
        self.execute_count = 0
        self.last_context: object = None

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        if self._target_stage is not None and stage != self._target_stage:
            return False
        return not (self._target_phase is not None and phase != self._target_phase)

    async def execute(self, context: object) -> None:
        self.execute_count += 1
        self.last_context = context


def _make_context(
    tmp_path: Path,
    stage: PipelineStage = PipelineStage.RESEARCH,
    stage_num: int = 2,
    gate_name: str = "research",
) -> MagicMock:
    """Build a mock PipelineContext with the required state."""
    ctx = MagicMock()
    ctx.require_workspace.return_value = tmp_path
    ctx.artifacts = ()
    ctx.state = {
        "current_stage_num": stage_num,
        "stage_spec": (stage, tmp_path / "step.md", tmp_path / "agent.md", gate_name),
        "gate_criteria": "",
        "elicitation": {},
    }
    return ctx


# ---------------------------------------------------------------------------
# stage_name
# ---------------------------------------------------------------------------


class TestStageName:
    def test_known_stage(self) -> None:
        assert stage_name(1) == "router"
        assert stage_name(5) == "layout-detective"
        assert stage_name(6) == "ffmpeg-engineer"
        assert stage_name(7) == "assembly"

    def test_unknown_stage(self) -> None:
        assert stage_name(99) == "stage-99"

    def test_zero(self) -> None:
        assert stage_name(0) == "stage-0"


# ---------------------------------------------------------------------------
# RunStageCommand — happy path
# ---------------------------------------------------------------------------


class TestRunStageCommandHappyPath:
    def test_stage_executes_returns_success(self, tmp_path: Path) -> None:
        """Stage runs successfully and returns a success result."""
        result = _make_reflection_result(escalation_needed=False, score=85)
        runner = _make_mock_runner(result)

        cmd = RunStageCommand(stage_runner=runner)
        ctx = _make_context(tmp_path)

        cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is True
        assert "completed" in cmd_result.message
        assert cmd_result.data["stage_num"] == 2
        assert cmd_result.data["stage"] == "research"
        assert cmd_result.data["score"] == 85
        assert runner.run_stage.await_count == 1


# ---------------------------------------------------------------------------
# RunStageCommand — hooks
# ---------------------------------------------------------------------------


class TestRunStageCommandHooks:
    def test_pre_hook_fires_for_correct_stage(self, tmp_path: Path) -> None:
        """Pre-hook fires when should_run returns True for the stage."""
        result = _make_reflection_result()
        runner = _make_mock_runner(result)
        hook = _StubHook(target_stage=PipelineStage.RESEARCH, target_phase="pre")

        cmd = RunStageCommand(stage_runner=runner, hooks=(hook,))
        ctx = _make_context(tmp_path, stage=PipelineStage.RESEARCH)

        asyncio.run(cmd.execute(ctx))

        assert hook.execute_count == 1

    def test_post_hook_fires_for_correct_stage(self, tmp_path: Path) -> None:
        """Post-hook fires when should_run returns True for the stage."""
        result = _make_reflection_result()
        runner = _make_mock_runner(result)
        hook = _StubHook(target_stage=PipelineStage.RESEARCH, target_phase="post")

        cmd = RunStageCommand(stage_runner=runner, hooks=(hook,))
        ctx = _make_context(tmp_path, stage=PipelineStage.RESEARCH)

        asyncio.run(cmd.execute(ctx))

        assert hook.execute_count == 1

    def test_hook_skipped_when_should_run_returns_false(self, tmp_path: Path) -> None:
        """Hook is not executed when should_run returns False."""
        result = _make_reflection_result()
        runner = _make_mock_runner(result)
        # Hook targets CONTENT but stage is RESEARCH
        hook = _StubHook(target_stage=PipelineStage.CONTENT, target_phase="pre")

        cmd = RunStageCommand(stage_runner=runner, hooks=(hook,))
        ctx = _make_context(tmp_path, stage=PipelineStage.RESEARCH)

        asyncio.run(cmd.execute(ctx))

        assert hook.execute_count == 0

    def test_multiple_hooks_only_matching_fire(self, tmp_path: Path) -> None:
        """With multiple hooks, only the ones matching the stage fire."""
        result = _make_reflection_result()
        runner = _make_mock_runner(result)

        hook_match_pre = _StubHook(target_stage=PipelineStage.RESEARCH, target_phase="pre")
        hook_match_post = _StubHook(target_stage=PipelineStage.RESEARCH, target_phase="post")
        hook_miss = _StubHook(target_stage=PipelineStage.CONTENT, target_phase="pre")

        cmd = RunStageCommand(stage_runner=runner, hooks=(hook_match_pre, hook_match_post, hook_miss))
        ctx = _make_context(tmp_path, stage=PipelineStage.RESEARCH)

        asyncio.run(cmd.execute(ctx))

        assert hook_match_pre.execute_count == 1
        assert hook_match_post.execute_count == 1
        assert hook_miss.execute_count == 0

    def test_post_hooks_fire_on_failure(self, tmp_path: Path) -> None:
        """Post-hooks still fire when the stage raises an exception."""
        runner = _make_mock_runner_raises(RuntimeError("stage crashed"))
        hook = _StubHook(target_stage=PipelineStage.RESEARCH, target_phase="post")

        cmd = RunStageCommand(stage_runner=runner, hooks=(hook,))
        ctx = _make_context(tmp_path, stage=PipelineStage.RESEARCH)

        with pytest.raises(RuntimeError, match="stage crashed"):
            asyncio.run(cmd.execute(ctx))

        assert hook.execute_count == 1

    def test_no_hooks_runs_without_error(self, tmp_path: Path) -> None:
        """Stage runs successfully even with no hooks configured."""
        result = _make_reflection_result()
        runner = _make_mock_runner(result)

        cmd = RunStageCommand(stage_runner=runner, hooks=())
        ctx = _make_context(tmp_path)

        cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is True


# ---------------------------------------------------------------------------
# RunStageCommand — escalation
# ---------------------------------------------------------------------------


class TestRunStageCommandEscalation:
    def test_escalation_returns_failure(self, tmp_path: Path) -> None:
        """Stage that escalates returns a failure CommandResult."""
        result = _make_reflection_result(escalation_needed=True, score=30)
        runner = _make_mock_runner(result)

        cmd = RunStageCommand(stage_runner=runner)
        ctx = _make_context(tmp_path)

        cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is False
        assert cmd_result.data["escalation_needed"] is True
        assert cmd_result.data["score"] == 30


# ---------------------------------------------------------------------------
# RunStageCommand — exception propagation
# ---------------------------------------------------------------------------


class TestRunStageCommandExceptionPropagation:
    def test_stage_failure_propagates(self, tmp_path: Path) -> None:
        """Exception from stage runner is propagated to caller."""
        runner = _make_mock_runner_raises(RuntimeError("network error"))

        cmd = RunStageCommand(stage_runner=runner)
        ctx = _make_context(tmp_path)

        with pytest.raises(RuntimeError, match="network error"):
            asyncio.run(cmd.execute(ctx))
