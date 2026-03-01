"""Tests for RunElicitationCommand and elicitation helper functions."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.cli.commands.run_elicitation import (
    MAX_ELICITATION_ROUNDS,
    MAX_QUESTIONS_PER_ROUND,
    RunElicitationCommand,
    collect_elicitation_answers,
    extract_elicitation_questions,
    find_router_output,
    is_interactive,
    parse_router_output,
    save_elicitation_context,
    validate_questions,
)
from pipeline.domain.enums import QADecision
from pipeline.domain.models import QACritique, ReflectionResult
from pipeline.domain.types import GateName

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubInputReader:
    """Stub InputReader for tests — returns pre-configured answers in sequence."""

    def __init__(self, answers: list[str | None]) -> None:
        self._answers = list(answers)
        self._call_count = 0

    async def read(self, prompt: str, timeout: int) -> str | None:
        if self._call_count >= len(self._answers):
            return None
        answer = self._answers[self._call_count]
        self._call_count += 1
        return answer


def _make_reflection_result(
    escalation_needed: bool = False,
    artifacts: tuple[Path, ...] = (),
    score: int = 80,
) -> ReflectionResult:
    """Create a real ReflectionResult for testing."""
    decision = QADecision.FAIL if escalation_needed else QADecision.PASS
    critique = QACritique(decision=decision, score=score, gate=GateName("router"), attempt=1)
    return ReflectionResult(
        best_critique=critique,
        artifacts=artifacts,
        attempts=1,
        escalation_needed=escalation_needed,
    )


def _write_router_output(path: Path, questions: list[str] | None = None) -> Path:
    """Write a router-output.json file and return its path."""
    data: dict[str, object] = {"url": "https://yt.com", "elicitation_questions": questions or []}
    f = path / "router-output.json"
    f.write_text(json.dumps(data))
    return f


def _make_stage_runner_mock(
    results: list[ReflectionResult],
    workspace: Path | None = None,
    questions_per_round: list[list[str]] | None = None,
) -> MagicMock:
    """Create a mock StageRunner that returns results in sequence.

    If workspace and questions_per_round are provided, writes router-output.json
    with the given questions on each call (to get a fresh mtime).
    """
    call_idx = [0]

    async def _side_effect(*args: object, **kwargs: object) -> ReflectionResult:
        idx = call_idx[0]
        call_idx[0] += 1
        if workspace and questions_per_round and idx < len(questions_per_round):
            _write_router_output(workspace, questions=questions_per_round[idx])
        return results[idx]

    mock = MagicMock()
    mock.run_stage = AsyncMock(side_effect=_side_effect)
    return mock


# ---------------------------------------------------------------------------
# is_interactive
# ---------------------------------------------------------------------------


class TestIsInteractive:
    def test_returns_true_when_tty(self) -> None:
        import sys as _sys

        with patch.object(_sys, "stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert is_interactive() is True

    def test_returns_false_when_not_tty(self) -> None:
        import sys as _sys

        with patch.object(_sys, "stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert is_interactive() is False

    def test_returns_false_when_no_isatty(self) -> None:
        import sys as _sys

        mock_stdin = MagicMock(spec=[])  # No isatty attribute
        with patch.object(_sys, "stdin", mock_stdin):
            assert is_interactive() is False


# ---------------------------------------------------------------------------
# find_router_output
# ---------------------------------------------------------------------------


class TestFindRouterOutput:
    def test_prefers_artifact_over_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        _write_router_output(workspace)

        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()
        artifact_file = _write_router_output(artifact_dir)

        result = find_router_output((artifact_file,), workspace)
        assert result == artifact_file

    def test_falls_back_to_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        workspace_file = _write_router_output(workspace)

        result = find_router_output((), workspace)
        assert result == workspace_file

    def test_returns_none_when_neither_exists(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        result = find_router_output((), workspace)
        assert result is None

    def test_skips_nonexistent_artifact(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ghost = tmp_path / "gone" / "router-output.json"

        result = find_router_output((ghost,), workspace)
        assert result is None

    def test_skips_stale_artifact(self, tmp_path: Path) -> None:
        artifact = _write_router_output(tmp_path)
        old_time = time.time() - 3600
        os.utime(artifact, (old_time, old_time))

        result = find_router_output((artifact,), tmp_path, min_mtime=time.time())
        assert result is None

    def test_skips_stale_workspace_fallback(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ws_file = _write_router_output(workspace)
        old_time = time.time() - 3600
        os.utime(ws_file, (old_time, old_time))

        result = find_router_output((), workspace, min_mtime=time.time())
        assert result is None


# ---------------------------------------------------------------------------
# parse_router_output
# ---------------------------------------------------------------------------


class TestParseRouterOutput:
    def test_parses_valid_json(self, tmp_path: Path) -> None:
        data = {"url": "https://yt.com", "elicitation_questions": []}
        _write_router_output(tmp_path)
        result = parse_router_output((), tmp_path)
        assert result == data

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert parse_router_output((), tmp_path) is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text("NOT JSON")
        assert parse_router_output((), tmp_path) is None

    def test_returns_none_for_non_dict_json(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text(json.dumps([1, 2, 3]))
        assert parse_router_output((), tmp_path) is None

    def test_handles_unicode_decode_error(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_bytes(b"\xff\xfe" + b"\x00" * 10)
        assert parse_router_output((), tmp_path) is None


# ---------------------------------------------------------------------------
# validate_questions
# ---------------------------------------------------------------------------


class TestValidateQuestions:
    def test_filters_valid_strings(self) -> None:
        raw = ["What is your name?", "How old are you?"]
        assert validate_questions(raw) == raw

    def test_skips_non_strings(self) -> None:
        raw: list[object] = ["Valid?", 42, None, {"key": "val"}, "Also valid?"]
        result = validate_questions(raw)
        assert result == ["Valid?", "Also valid?"]

    def test_skips_empty_and_whitespace_strings(self) -> None:
        raw: list[object] = ["", "  ", "Valid?", "\t"]
        result = validate_questions(raw)
        assert result == ["Valid?"]

    def test_caps_at_max(self) -> None:
        raw = [f"Q{i}?" for i in range(20)]
        result = validate_questions(raw)
        assert len(result) == MAX_QUESTIONS_PER_ROUND

    def test_strips_whitespace(self) -> None:
        raw = ["  What?  ", "\tWhy?\n"]
        assert validate_questions(raw) == ["What?", "Why?"]

    def test_empty_list(self) -> None:
        assert validate_questions([]) == []


# ---------------------------------------------------------------------------
# collect_elicitation_answers
# ---------------------------------------------------------------------------


class TestCollectElicitationAnswers:
    def test_happy_path(self) -> None:
        reader = _StubInputReader(["answer1", "answer2"])
        result = asyncio.run(collect_elicitation_answers(["Q1?", "Q2?"], reader))
        assert result == {"Q1?": "answer1", "Q2?": "answer2"}

    def test_skips_empty_answers(self) -> None:
        reader = _StubInputReader(["", "answer2"])
        result = asyncio.run(collect_elicitation_answers(["Q1?", "Q2?"], reader))
        assert result == {"Q2?": "answer2"}

    def test_stops_on_timeout(self) -> None:
        reader = _StubInputReader(["answer1", None])
        result = asyncio.run(collect_elicitation_answers(["Q1?", "Q2?"], reader))
        assert result == {"Q1?": "answer1"}

    def test_all_cancelled(self) -> None:
        reader = _StubInputReader([None])
        result = asyncio.run(collect_elicitation_answers(["Q1?"], reader))
        assert result == {}


# ---------------------------------------------------------------------------
# save_elicitation_context
# ---------------------------------------------------------------------------


class TestSaveElicitationContext:
    def test_saves_json(self, tmp_path: Path) -> None:
        context = {"Q1?": "A1", "Q2?": "A2"}
        save_elicitation_context(tmp_path, context)
        saved = json.loads((tmp_path / "elicitation-context.json").read_text())
        assert saved == context

    def test_logs_warning_on_write_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        with patch("tempfile.mkstemp", side_effect=OSError("disk full")):
            save_elicitation_context(tmp_path, {"Q?": "A"})
        assert "Failed to save elicitation context" in caplog.text


# ---------------------------------------------------------------------------
# extract_elicitation_questions
# ---------------------------------------------------------------------------


class TestExtractElicitationQuestions:
    def test_returns_none_when_no_escalation(self, tmp_path: Path) -> None:
        result = _make_reflection_result(escalation_needed=False)
        assert extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_none_when_no_router_output(self, tmp_path: Path) -> None:
        result = _make_reflection_result(escalation_needed=True)
        assert extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_none_when_no_questions(self, tmp_path: Path) -> None:
        _write_router_output(tmp_path, questions=[])
        result = _make_reflection_result(escalation_needed=True)
        assert extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_questions_when_present(self, tmp_path: Path) -> None:
        _write_router_output(tmp_path, questions=["What URL?"])
        result = _make_reflection_result(escalation_needed=True)
        questions = extract_elicitation_questions(result, (), tmp_path)
        assert questions == ["What URL?"]

    def test_returns_none_for_non_list_questions(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text(json.dumps({"elicitation_questions": "not a list"}))
        result = _make_reflection_result(escalation_needed=True)
        assert extract_elicitation_questions(result, (), tmp_path) is None

    def test_prefers_artifact_file(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        _write_router_output(workspace, questions=[])

        artifact = _write_router_output(tmp_path, questions=["From artifact?"])

        result = _make_reflection_result(escalation_needed=True)
        questions = extract_elicitation_questions(result, (artifact,), workspace)
        assert questions == ["From artifact?"]


# ---------------------------------------------------------------------------
# RunElicitationCommand (async integration tests)
# ---------------------------------------------------------------------------


class TestRunElicitationCommand:
    """Async tests for the RunElicitationCommand."""

    def _make_context(self, tmp_path: Path, runner: MagicMock) -> MagicMock:
        """Build a mock PipelineContext with the required state."""
        ctx = MagicMock()
        ctx.require_workspace.return_value = tmp_path
        ctx.artifacts = ()
        ctx.state = {
            "step_file": tmp_path / "step.md",
            "agent_def": tmp_path / "agent.md",
            "gate": GateName("router"),
            "gate_criteria": "",
            "elicitation": {"telegram_message": "test"},
        }
        return ctx

    def test_passes_through_on_success(self, tmp_path: Path) -> None:
        """Router passes QA on first try — no elicitation needed."""
        result = _make_reflection_result(escalation_needed=False)
        runner = _make_stage_runner_mock([result])
        reader = _StubInputReader([])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is True
        assert runner.run_stage.await_count == 1
        assert not (tmp_path / "elicitation-context.json").exists()

    def test_escalation_without_questions_returns_failure(self, tmp_path: Path) -> None:
        """Router escalates but no elicitation_questions in output — genuine failure."""
        result = _make_reflection_result(escalation_needed=True)
        runner = _make_stage_runner_mock([result])
        reader = _StubInputReader([])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is False
        assert cmd_result.data["escalation_needed"] is True
        assert runner.run_stage.await_count == 1

    def test_elicitation_loop_re_runs_router(self, tmp_path: Path) -> None:
        """Router asks questions, user answers, router passes on re-run."""
        fail_result = _make_reflection_result(escalation_needed=True)
        pass_result = _make_reflection_result(escalation_needed=False)
        runner = _make_stage_runner_mock(
            [fail_result, pass_result],
            workspace=tmp_path,
            questions_per_round=[["What URL?"], []],
        )
        reader = _StubInputReader(["https://yt.com"])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        with patch(
            "pipeline.application.cli.commands.run_elicitation.is_interactive",
            return_value=True,
        ):
            cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is True
        assert runner.run_stage.await_count == 2
        # Answers persisted via finally block
        assert (tmp_path / "elicitation-context.json").exists()
        saved = json.loads((tmp_path / "elicitation-context.json").read_text())
        assert saved == {"What URL?": "https://yt.com"}

    def test_non_interactive_skips_prompting(self, tmp_path: Path) -> None:
        """Non-interactive stdin falls back to defaults without blocking."""
        fail_result = _make_reflection_result(escalation_needed=True)
        runner = _make_stage_runner_mock(
            [fail_result],
            workspace=tmp_path,
            questions_per_round=[["What URL?"]],
        )
        reader = _StubInputReader([])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        with patch(
            "pipeline.application.cli.commands.run_elicitation.is_interactive",
            return_value=False,
        ):
            cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is False
        assert cmd_result.data["escalation_needed"] is True
        assert runner.run_stage.await_count == 1

    def test_max_rounds_cap(self, tmp_path: Path) -> None:
        """After MAX_ELICITATION_ROUNDS, stops prompting and returns."""
        fail_results = [_make_reflection_result(escalation_needed=True) for _ in range(4)]
        runner = _make_stage_runner_mock(
            fail_results,
            workspace=tmp_path,
            questions_per_round=[["Same question?"]] * 4,
        )
        reader = _StubInputReader(["answer"] * 4)

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        with patch(
            "pipeline.application.cli.commands.run_elicitation.is_interactive",
            return_value=True,
        ):
            cmd_result = asyncio.run(cmd.execute(ctx))

        # Initial run + MAX_ELICITATION_ROUNDS re-runs = 3 total
        assert runner.run_stage.await_count == MAX_ELICITATION_ROUNDS + 1
        assert cmd_result.success is False
        # Answers still persisted
        assert (tmp_path / "elicitation-context.json").exists()

    def test_empty_answers_returns_immediately(self, tmp_path: Path) -> None:
        """User provides no answers — use defaults without re-running."""
        fail_result = _make_reflection_result(escalation_needed=True)
        runner = _make_stage_runner_mock(
            [fail_result],
            workspace=tmp_path,
            questions_per_round=[["What URL?"]],
        )
        # Empty string answer means the user hit enter without typing
        reader = _StubInputReader([""])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        with patch(
            "pipeline.application.cli.commands.run_elicitation.is_interactive",
            return_value=True,
        ):
            asyncio.run(cmd.execute(ctx))

        assert runner.run_stage.await_count == 1
        # No context saved since no answers accumulated
        assert not (tmp_path / "elicitation-context.json").exists()

    def test_answers_persisted_on_escalation(self, tmp_path: Path) -> None:
        """Answers from round 1 are persisted even when round 2 escalates without questions."""
        fail_with_questions = _make_reflection_result(escalation_needed=True)
        fail_without_questions = _make_reflection_result(escalation_needed=True)

        call_count = [0]

        def _extract_side_effect(
            result: object,
            artifacts: tuple[Path, ...],
            workspace: Path,
            min_mtime: float = 0.0,
        ) -> list[str] | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return ["What URL?"]
            return None

        runner = _make_stage_runner_mock([fail_with_questions, fail_without_questions])
        reader = _StubInputReader(["https://yt.com"])

        cmd = RunElicitationCommand(input_reader=reader, stage_runner=runner)
        ctx = self._make_context(tmp_path, runner)

        with (
            patch(
                "pipeline.application.cli.commands.run_elicitation.is_interactive",
                return_value=True,
            ),
            patch(
                "pipeline.application.cli.commands.run_elicitation.extract_elicitation_questions",
                side_effect=_extract_side_effect,
            ),
        ):
            cmd_result = asyncio.run(cmd.execute(ctx))

        assert cmd_result.success is False
        assert cmd_result.data["escalation_needed"] is True
        # Answers persisted via finally block even though pipeline escalated
        assert (tmp_path / "elicitation-context.json").exists()
        saved = json.loads((tmp_path / "elicitation-context.json").read_text())
        assert saved == {"What URL?": "https://yt.com"}
