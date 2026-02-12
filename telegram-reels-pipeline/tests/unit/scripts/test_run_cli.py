"""Tests for scripts/run_cli.py elicitation helpers."""

# ruff: noqa: E402, I001

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add scripts parent so we can import run_cli — must precede the import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))
import run_cli

from pipeline.domain.enums import QADecision
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


# ---------------------------------------------------------------------------
# _is_interactive
# ---------------------------------------------------------------------------


class TestIsInteractive:
    def test_returns_true_when_tty(self) -> None:
        with patch.object(sys, "stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert run_cli._is_interactive() is True

    def test_returns_false_when_not_tty(self) -> None:
        with patch.object(sys, "stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert run_cli._is_interactive() is False

    def test_returns_false_when_no_isatty(self) -> None:
        mock_stdin = MagicMock(spec=[])  # No isatty attribute
        with patch.object(sys, "stdin", mock_stdin):
            assert run_cli._is_interactive() is False


# ---------------------------------------------------------------------------
# _find_router_output
# ---------------------------------------------------------------------------


class TestFindRouterOutput:
    def test_prefers_artifact_over_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        _write_router_output(workspace)

        artifact_dir = tmp_path / "artifacts"
        artifact_dir.mkdir()
        artifact_file = _write_router_output(artifact_dir)

        result = run_cli._find_router_output((artifact_file,), workspace)
        assert result == artifact_file

    def test_falls_back_to_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        workspace_file = _write_router_output(workspace)

        result = run_cli._find_router_output((), workspace)
        assert result == workspace_file

    def test_returns_none_when_neither_exists(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        result = run_cli._find_router_output((), workspace)
        assert result is None

    def test_skips_nonexistent_artifact(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ghost = tmp_path / "gone" / "router-output.json"

        result = run_cli._find_router_output((ghost,), workspace)
        assert result is None

    def test_skips_stale_artifact(self, tmp_path: Path) -> None:
        artifact = _write_router_output(tmp_path)
        # Set mtime to 1 hour ago
        old_time = time.time() - 3600
        os.utime(artifact, (old_time, old_time))

        result = run_cli._find_router_output((artifact,), tmp_path, min_mtime=time.time())
        assert result is None

    def test_skips_stale_workspace_fallback(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        ws_file = _write_router_output(workspace)
        old_time = time.time() - 3600
        os.utime(ws_file, (old_time, old_time))

        result = run_cli._find_router_output((), workspace, min_mtime=time.time())
        assert result is None

    def test_accepts_fresh_file(self, tmp_path: Path) -> None:
        before = time.time() - 1
        artifact = _write_router_output(tmp_path)

        result = run_cli._find_router_output((artifact,), tmp_path, min_mtime=before)
        assert result == artifact


# ---------------------------------------------------------------------------
# _parse_router_output
# ---------------------------------------------------------------------------


class TestParseRouterOutput:
    def test_parses_valid_json(self, tmp_path: Path) -> None:
        data = {"url": "https://yt.com", "elicitation_questions": []}
        _write_router_output(tmp_path)
        result = run_cli._parse_router_output((), tmp_path)
        assert result == data

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        assert run_cli._parse_router_output((), tmp_path) is None

    def test_returns_none_for_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text("NOT JSON")
        assert run_cli._parse_router_output((), tmp_path) is None

    def test_returns_none_for_non_dict_json(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text(json.dumps([1, 2, 3]))
        assert run_cli._parse_router_output((), tmp_path) is None

    def test_handles_unicode_decode_error(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_bytes(b"\xff\xfe" + b"\x00" * 10)
        assert run_cli._parse_router_output((), tmp_path) is None


# ---------------------------------------------------------------------------
# _validate_questions
# ---------------------------------------------------------------------------


class TestValidateQuestions:
    def test_filters_valid_strings(self) -> None:
        raw = ["What is your name?", "How old are you?"]
        assert run_cli._validate_questions(raw) == raw

    def test_skips_non_strings(self) -> None:
        raw = ["Valid?", 42, None, {"key": "val"}, "Also valid?"]
        result = run_cli._validate_questions(raw)
        assert result == ["Valid?", "Also valid?"]

    def test_skips_empty_and_whitespace_strings(self) -> None:
        raw = ["", "  ", "Valid?", "\t"]
        result = run_cli._validate_questions(raw)
        assert result == ["Valid?"]

    def test_caps_at_max(self) -> None:
        raw = [f"Q{i}?" for i in range(20)]
        result = run_cli._validate_questions(raw)
        assert len(result) == run_cli.MAX_QUESTIONS_PER_ROUND

    def test_strips_whitespace(self) -> None:
        raw = ["  What?  ", "\tWhy?\n"]
        assert run_cli._validate_questions(raw) == ["What?", "Why?"]

    def test_empty_list(self) -> None:
        assert run_cli._validate_questions([]) == []


# ---------------------------------------------------------------------------
# _timed_input
# ---------------------------------------------------------------------------


class TestTimedInput:
    def test_returns_stripped_input(self) -> None:
        with patch("builtins.input", return_value="  hello  "):
            result = asyncio.run(run_cli._timed_input("> ", timeout=5))
            assert result == "hello"

    def test_returns_none_on_eof(self) -> None:
        with patch("builtins.input", side_effect=EOFError):
            result = asyncio.run(run_cli._timed_input("> "))
            assert result is None

    def test_returns_none_on_keyboard_interrupt(self) -> None:
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = asyncio.run(run_cli._timed_input("> "))
            assert result is None

    def test_returns_none_on_timeout(self) -> None:
        import threading

        barrier = threading.Event()

        def blocking_input(prompt: str) -> str:
            barrier.wait(timeout=5)
            return ""

        with patch("builtins.input", side_effect=blocking_input):
            result = asyncio.run(run_cli._timed_input("> ", timeout=0.05))
            barrier.set()
        assert result is None


# ---------------------------------------------------------------------------
# _collect_elicitation_answers
# ---------------------------------------------------------------------------


class TestCollectElicitationAnswers:
    def test_happy_path(self) -> None:
        with patch.object(run_cli, "_timed_input", new=AsyncMock(side_effect=["answer1", "answer2"])):
            result = asyncio.run(run_cli._collect_elicitation_answers(["Q1?", "Q2?"]))
        assert result == {"Q1?": "answer1", "Q2?": "answer2"}

    def test_skips_empty_answers(self) -> None:
        with patch.object(run_cli, "_timed_input", new=AsyncMock(side_effect=["", "answer2"])):
            result = asyncio.run(run_cli._collect_elicitation_answers(["Q1?", "Q2?"]))
        assert result == {"Q2?": "answer2"}

    def test_stops_on_timeout(self) -> None:
        with patch.object(run_cli, "_timed_input", new=AsyncMock(side_effect=["answer1", None])):
            result = asyncio.run(run_cli._collect_elicitation_answers(["Q1?", "Q2?"]))
        assert result == {"Q1?": "answer1"}

    def test_all_cancelled(self) -> None:
        with patch.object(run_cli, "_timed_input", new=AsyncMock(return_value=None)):
            result = asyncio.run(run_cli._collect_elicitation_answers(["Q1?"]))
        assert result == {}


# ---------------------------------------------------------------------------
# _save_elicitation_context
# ---------------------------------------------------------------------------


class TestSaveElicitationContext:
    def test_saves_json(self, tmp_path: Path) -> None:
        context = {"Q1?": "A1", "Q2?": "A2"}
        run_cli._save_elicitation_context(tmp_path, context)
        saved = json.loads((tmp_path / "elicitation-context.json").read_text())
        assert saved == context

    def test_logs_warning_on_write_failure(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        with patch("tempfile.mkstemp", side_effect=OSError("disk full")):
            run_cli._save_elicitation_context(tmp_path, {"Q?": "A"})
        assert "Failed to save elicitation context" in caplog.text


# ---------------------------------------------------------------------------
# _extract_elicitation_questions
# ---------------------------------------------------------------------------


class TestExtractElicitationQuestions:
    def test_returns_none_when_no_escalation(self, tmp_path: Path) -> None:
        result = _make_reflection_result(escalation_needed=False)
        assert run_cli._extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_none_when_no_router_output(self, tmp_path: Path) -> None:
        result = _make_reflection_result(escalation_needed=True)
        assert run_cli._extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_none_when_no_questions(self, tmp_path: Path) -> None:
        _write_router_output(tmp_path, questions=[])
        result = _make_reflection_result(escalation_needed=True)
        assert run_cli._extract_elicitation_questions(result, (), tmp_path) is None

    def test_returns_questions_when_present(self, tmp_path: Path) -> None:
        _write_router_output(tmp_path, questions=["What URL?"])
        result = _make_reflection_result(escalation_needed=True)
        questions = run_cli._extract_elicitation_questions(result, (), tmp_path)
        assert questions == ["What URL?"]

    def test_returns_none_for_non_list_questions(self, tmp_path: Path) -> None:
        f = tmp_path / "router-output.json"
        f.write_text(json.dumps({"elicitation_questions": "not a list"}))
        result = _make_reflection_result(escalation_needed=True)
        assert run_cli._extract_elicitation_questions(result, (), tmp_path) is None

    def test_prefers_artifact_file(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        _write_router_output(workspace, questions=[])

        artifact = _write_router_output(tmp_path, questions=["From artifact?"])

        result = _make_reflection_result(escalation_needed=True)
        questions = run_cli._extract_elicitation_questions(result, (artifact,), workspace)
        assert questions == ["From artifact?"]


# ---------------------------------------------------------------------------
# _run_router_with_elicitation (async integration tests)
# ---------------------------------------------------------------------------


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


class TestRunRouterWithElicitation:
    """Async tests for the elicitation loop orchestrator."""

    def test_passes_through_on_success(self, tmp_path: Path) -> None:
        """Router passes QA on first try — no elicitation needed."""
        result = _make_reflection_result(escalation_needed=False)
        runner = _make_stage_runner_mock([result])

        got_result, got_artifacts = asyncio.run(
            run_cli._run_router_with_elicitation(
                elicitation={"telegram_message": "test"},
                step_file=tmp_path / "step.md",
                agent_def=tmp_path / "agent.md",
                artifacts=(),
                stage_runner=runner,
                gate=GateName("router"),
                gate_criteria="",
                workspace=tmp_path,
            )
        )

        assert got_result.escalation_needed is False
        assert runner.run_stage.await_count == 1
        assert not (tmp_path / "elicitation-context.json").exists()

    def test_escalation_without_questions_returns_immediately(self, tmp_path: Path) -> None:
        """Router escalates but no elicitation_questions in output — genuine failure."""
        result = _make_reflection_result(escalation_needed=True)
        runner = _make_stage_runner_mock([result])

        got_result, _ = asyncio.run(
            run_cli._run_router_with_elicitation(
                elicitation={"telegram_message": "test"},
                step_file=tmp_path / "step.md",
                agent_def=tmp_path / "agent.md",
                artifacts=(),
                stage_runner=runner,
                gate=GateName("router"),
                gate_criteria="",
                workspace=tmp_path,
            )
        )

        assert got_result.escalation_needed is True
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

        with (
            patch.object(run_cli, "_is_interactive", return_value=True),
            patch.object(
                run_cli,
                "_collect_elicitation_answers",
                new=AsyncMock(return_value={"What URL?": "https://yt.com"}),
            ),
        ):
            got_result, _ = asyncio.run(
                run_cli._run_router_with_elicitation(
                    elicitation={"telegram_message": "test"},
                    step_file=tmp_path / "step.md",
                    agent_def=tmp_path / "agent.md",
                    artifacts=(),
                    stage_runner=runner,
                    gate=GateName("router"),
                    gate_criteria="",
                    workspace=tmp_path,
                )
            )

        assert got_result.escalation_needed is False
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

        with patch.object(run_cli, "_is_interactive", return_value=False):
            got_result, _ = asyncio.run(
                run_cli._run_router_with_elicitation(
                    elicitation={"telegram_message": "test"},
                    step_file=tmp_path / "step.md",
                    agent_def=tmp_path / "agent.md",
                    artifacts=(),
                    stage_runner=runner,
                    gate=GateName("router"),
                    gate_criteria="",
                    workspace=tmp_path,
                )
            )

        assert got_result.escalation_needed is True
        assert runner.run_stage.await_count == 1

    def test_max_rounds_cap(self, tmp_path: Path) -> None:
        """After MAX_ELICITATION_ROUNDS, stops prompting and returns."""
        fail_results = [_make_reflection_result(escalation_needed=True) for _ in range(4)]
        runner = _make_stage_runner_mock(
            fail_results,
            workspace=tmp_path,
            questions_per_round=[["Same question?"]] * 4,
        )

        with (
            patch.object(run_cli, "_is_interactive", return_value=True),
            patch.object(
                run_cli,
                "_collect_elicitation_answers",
                new=AsyncMock(return_value={"Same question?": "answer"}),
            ),
        ):
            got_result, _ = asyncio.run(
                run_cli._run_router_with_elicitation(
                    elicitation={"telegram_message": "test"},
                    step_file=tmp_path / "step.md",
                    agent_def=tmp_path / "agent.md",
                    artifacts=(),
                    stage_runner=runner,
                    gate=GateName("router"),
                    gate_criteria="",
                    workspace=tmp_path,
                )
            )

        # Initial run + MAX_ELICITATION_ROUNDS re-runs = 3 total
        assert runner.run_stage.await_count == run_cli.MAX_ELICITATION_ROUNDS + 1
        assert got_result.escalation_needed is True
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

        with (
            patch.object(run_cli, "_is_interactive", return_value=True),
            patch.object(run_cli, "_collect_elicitation_answers", new=AsyncMock(return_value={})),
        ):
            got_result, _ = asyncio.run(
                run_cli._run_router_with_elicitation(
                    elicitation={"telegram_message": "test"},
                    step_file=tmp_path / "step.md",
                    agent_def=tmp_path / "agent.md",
                    artifacts=(),
                    stage_runner=runner,
                    gate=GateName("router"),
                    gate_criteria="",
                    workspace=tmp_path,
                )
            )

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
            artifacts: tuple,
            workspace: Path,
            min_mtime: float = 0.0,
        ) -> list[str] | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return ["What URL?"]
            return None

        runner = _make_stage_runner_mock([fail_with_questions, fail_without_questions])

        with (
            patch.object(run_cli, "_is_interactive", return_value=True),
            patch.object(
                run_cli,
                "_collect_elicitation_answers",
                new=AsyncMock(return_value={"What URL?": "https://yt.com"}),
            ),
            patch.object(run_cli, "_extract_elicitation_questions", side_effect=_extract_side_effect),
        ):
            got_result, _ = asyncio.run(
                run_cli._run_router_with_elicitation(
                    elicitation={"telegram_message": "test"},
                    step_file=tmp_path / "step.md",
                    agent_def=tmp_path / "agent.md",
                    artifacts=(),
                    stage_runner=runner,
                    gate=GateName("router"),
                    gate_criteria="",
                    workspace=tmp_path,
                )
            )

        assert got_result.escalation_needed is True
        # Answers persisted via finally block even though pipeline escalated
        assert (tmp_path / "elicitation-context.json").exists()
        saved = json.loads((tmp_path / "elicitation-context.json").read_text())
        assert saved == {"What URL?": "https://yt.com"}
