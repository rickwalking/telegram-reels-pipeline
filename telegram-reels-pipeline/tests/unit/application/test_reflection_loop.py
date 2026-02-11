"""Tests for ReflectionLoop — QA reflection with retry and best-of-three."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from pipeline.application.reflection_loop import (
    ReflectionLoop,
    _build_artifact_section,
    _extract_json_object,
    _parse_critique,
    select_best,
)
from pipeline.domain.enums import PipelineStage, QADecision
from pipeline.domain.errors import QAError
from pipeline.domain.models import AgentRequest, AgentResult, QACritique, ReflectionResult
from pipeline.domain.transitions import MAX_QA_ATTEMPTS
from pipeline.domain.types import GateName


@pytest.fixture
def step_file(tmp_path: Path) -> Path:
    f = tmp_path / "step.md"
    f.write_text("Run the router stage.")
    return f


@pytest.fixture
def agent_def(tmp_path: Path) -> Path:
    f = tmp_path / "agent.md"
    f.write_text("You are the Router Agent.")
    return f


@pytest.fixture
def request_(step_file: Path, agent_def: Path) -> AgentRequest:
    return AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)


@pytest.fixture
def gate() -> GateName:
    return GateName("router")


@pytest.fixture
def gate_criteria() -> str:
    return "Validate router output completeness."


def _make_qa_json(
    decision: str = "PASS",
    score: int = 90,
    gate: str = "router",
    attempt: int = 1,
    blockers: list[dict[str, str]] | None = None,
    fixes: list[str] | None = None,
    confidence: float = 0.9,
) -> str:
    return json.dumps(
        {
            "decision": decision,
            "score": score,
            "gate": gate,
            "attempt": attempt,
            "blockers": blockers or [],
            "prescriptive_fixes": fixes or [],
            "confidence": confidence,
        }
    )


def _make_agent_result(artifacts: tuple[Path, ...] = ()) -> AgentResult:
    return AgentResult(status="completed", artifacts=artifacts, duration_seconds=1.0)


class TestParseCritique:
    def test_parses_valid_pass(self) -> None:
        raw = _make_qa_json(decision="PASS", score=92)
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.decision == QADecision.PASS
        assert result.score == 92
        assert result.gate == GateName("router")
        assert result.attempt == 1

    def test_parses_rework_with_fixes(self) -> None:
        raw = _make_qa_json(decision="REWORK", score=60, fixes=["Fix the format", "Add headers"])
        result = _parse_critique(raw, GateName("router"), 2)
        assert result.decision == QADecision.REWORK
        assert result.prescriptive_fixes == ("Fix the format", "Add headers")

    def test_parses_fail_with_blockers(self) -> None:
        raw = _make_qa_json(
            decision="FAIL",
            score=20,
            blockers=[{"severity": "critical", "description": "Missing output"}],
        )
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.decision == QADecision.FAIL
        assert len(result.blockers) == 1

    def test_strips_markdown_code_fences(self) -> None:
        raw = "```json\n" + _make_qa_json() + "\n```"
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.decision == QADecision.PASS

    def test_parses_json_with_trailing_text(self) -> None:
        raw = _make_qa_json(decision="PASS", score=88) + "\n\nSome explanation text after."
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.decision == QADecision.PASS
        assert result.score == 88

    def test_parses_json_with_leading_text(self) -> None:
        raw = "Here is my evaluation:\n\n" + _make_qa_json(decision="REWORK", score=60)
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.decision == QADecision.REWORK

    def test_invalid_json_raises_qa_error(self) -> None:
        with pytest.raises(QAError, match="no valid JSON object"):
            _parse_critique("not json at all", GateName("router"), 1)

    def test_non_object_raises_qa_error(self) -> None:
        with pytest.raises(QAError, match="no valid JSON object"):
            _parse_critique("[1, 2, 3]", GateName("router"), 1)

    def test_missing_decision_raises_qa_error(self) -> None:
        with pytest.raises(QAError, match="decision"):
            _parse_critique('{"score": 90}', GateName("router"), 1)

    def test_invalid_decision_raises_qa_error(self) -> None:
        with pytest.raises(QAError, match="decision"):
            _parse_critique('{"decision": "MAYBE"}', GateName("router"), 1)

    def test_confidence_and_score_parsed(self) -> None:
        raw = _make_qa_json(score=75, confidence=0.85)
        result = _parse_critique(raw, GateName("router"), 1)
        assert result.score == 75
        assert result.confidence == 0.85


class TestSelectBest:
    def test_selects_highest_score(self) -> None:
        low = QACritique(decision=QADecision.REWORK, score=50, gate=GateName("r"), attempt=1, confidence=0.5)
        mid = QACritique(decision=QADecision.REWORK, score=70, gate=GateName("r"), attempt=2, confidence=0.7)
        high = QACritique(decision=QADecision.REWORK, score=80, gate=GateName("r"), attempt=3, confidence=0.8)
        result_low = _make_agent_result()
        result_mid = _make_agent_result()
        result_high = _make_agent_result()

        best_critique, best_result = select_best([(low, result_low), (mid, result_mid), (high, result_high)])
        assert best_critique.score == 80
        assert best_result is result_high

    def test_empty_raises_qa_error(self) -> None:
        with pytest.raises(QAError, match="No QA attempts"):
            select_best([])

    def test_single_attempt(self) -> None:
        critique = QACritique(decision=QADecision.FAIL, score=30, gate=GateName("r"), attempt=1, confidence=0.3)
        result = _make_agent_result()
        best_c, best_r = select_best([(critique, result)])
        assert best_c.score == 30


class TestReflectionLoopEvaluate:
    async def test_evaluate_returns_critique(self, request_: AgentRequest, gate: GateName) -> None:
        model_port = AsyncMock()
        model_port.dispatch.return_value = _make_qa_json(decision="PASS", score=88)
        agent_port = AsyncMock()

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        critique = await loop.evaluate((), gate, "criteria text", 1)

        assert critique.decision == QADecision.PASS
        assert critique.score == 88
        model_port.dispatch.assert_called_once()

    async def test_evaluate_raises_on_bad_response(self, gate: GateName) -> None:
        model_port = AsyncMock()
        model_port.dispatch.return_value = "garbage"
        agent_port = AsyncMock()

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        with pytest.raises(QAError):
            await loop.evaluate((), gate, "criteria", 1)


class TestReflectionLoopRun:
    async def test_pass_on_first_attempt(self, request_: AgentRequest, gate: GateName, gate_criteria: str) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.return_value = _make_qa_json(decision="PASS", score=92)

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop.run(request_, gate, gate_criteria)

        assert isinstance(result, ReflectionResult)
        assert result.best_critique.decision == QADecision.PASS
        assert result.attempts == 1
        assert not result.escalation_needed
        agent_port.execute.assert_called_once()

    async def test_rework_then_pass(self, request_: AgentRequest, gate: GateName, gate_criteria: str) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=60, fixes=["Fix X"]),
            _make_qa_json(decision="PASS", score=85),
        ]

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop.run(request_, gate, gate_criteria)

        assert result.best_critique.decision == QADecision.PASS
        assert result.attempts == 2
        assert not result.escalation_needed
        assert agent_port.execute.call_count == 2

    async def test_three_reworks_selects_best(self, request_: AgentRequest, gate: GateName, gate_criteria: str) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=50),
            _make_qa_json(decision="REWORK", score=70),
            _make_qa_json(decision="REWORK", score=60),
        ]

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop.run(request_, gate, gate_criteria)

        assert result.best_critique.score == 70
        assert result.attempts == 3
        assert not result.escalation_needed  # 70 >= MIN_SCORE_THRESHOLD

    async def test_fail_skips_to_best_of_three(
        self, request_: AgentRequest, gate: GateName, gate_criteria: str
    ) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=55),
            _make_qa_json(decision="FAIL", score=20),
        ]

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop.run(request_, gate, gate_criteria)

        assert result.best_critique.score == 55
        assert result.attempts == 2

    async def test_escalation_when_best_score_below_threshold(
        self, request_: AgentRequest, gate: GateName, gate_criteria: str
    ) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=20),
            _make_qa_json(decision="REWORK", score=30),
            _make_qa_json(decision="REWORK", score=25),
        ]

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop.run(request_, gate, gate_criteria)

        assert result.escalation_needed
        assert result.best_critique.score == 30  # best of three

    async def test_prescriptive_fixes_passed_in_attempt_history(
        self, request_: AgentRequest, gate: GateName, gate_criteria: str
    ) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=60, fixes=["Fix the header"]),
            _make_qa_json(decision="PASS", score=90),
        ]

        loop = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        await loop.run(request_, gate, gate_criteria)

        # Second call should have attempt_history with the prescriptive fix
        second_call_request = agent_port.execute.call_args_list[1][0][0]
        assert len(second_call_request.attempt_history) == 1
        assert "Fix the header" in second_call_request.attempt_history[0]["prescriptive_fixes"]

    async def test_custom_min_score_threshold(self, request_: AgentRequest, gate: GateName, gate_criteria: str) -> None:
        agent_port = AsyncMock()
        agent_port.execute.return_value = _make_agent_result()
        model_port = AsyncMock()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=50),
            _make_qa_json(decision="REWORK", score=55),
            _make_qa_json(decision="REWORK", score=45),
        ]

        # With default threshold (40), score 55 would NOT escalate
        loop_default = ReflectionLoop(agent_port=agent_port, model_port=model_port)
        result = await loop_default.run(request_, gate, gate_criteria)
        assert not result.escalation_needed

        # With custom threshold (60), score 55 SHOULD escalate
        agent_port.execute.return_value = _make_agent_result()
        model_port.dispatch.side_effect = [
            _make_qa_json(decision="REWORK", score=50),
            _make_qa_json(decision="REWORK", score=55),
            _make_qa_json(decision="REWORK", score=45),
        ]
        loop_custom = ReflectionLoop(agent_port=agent_port, model_port=model_port, min_score_threshold=60)
        result = await loop_custom.run(request_, gate, gate_criteria)
        assert result.escalation_needed

    async def test_max_attempts_constant_is_three(self) -> None:
        assert MAX_QA_ATTEMPTS == 3


class TestExtractJsonObject:
    def test_direct_json(self) -> None:
        data = _extract_json_object('{"key": "value"}')
        assert data == {"key": "value"}

    def test_json_in_fences(self) -> None:
        data = _extract_json_object('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}

    def test_json_with_trailing_text(self) -> None:
        data = _extract_json_object('{"key": "value"}\n\nSome extra text')
        assert data == {"key": "value"}

    def test_json_with_leading_text(self) -> None:
        data = _extract_json_object('Explanation:\n{"key": "value"}')
        assert data == {"key": "value"}

    def test_returns_none_for_array(self) -> None:
        assert _extract_json_object("[1, 2, 3]") is None

    def test_returns_none_for_plain_text(self) -> None:
        assert _extract_json_object("no json here") is None

    def test_returns_none_for_empty(self) -> None:
        assert _extract_json_object("") is None


class TestBuildArtifactSection:
    def test_empty_artifacts(self) -> None:
        result = _build_artifact_section(())
        assert "No artifacts produced" in result

    def test_inlines_text_file(self, tmp_path: Path) -> None:
        f = tmp_path / "output.json"
        f.write_text('{"url": "test"}')
        result = _build_artifact_section((f,))
        assert "output.json" in result
        assert '{"url": "test"}' in result
        assert "~~~~" in result

    def test_inlines_multiple_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "data.json"
        f1.write_text("{}")
        f2 = tmp_path / "notes.md"
        f2.write_text("# Notes")
        result = _build_artifact_section((f1, f2))
        assert "data.json" in result
        assert "notes.md" in result

    def test_shows_metadata_for_large_files(self, tmp_path: Path) -> None:
        f = tmp_path / "huge.json"
        f.write_text("x" * 60_000)
        result = _build_artifact_section((f,))
        assert "binary/large" in result
        assert "60000 bytes" in result

    def test_shows_metadata_for_binary_files(self, tmp_path: Path) -> None:
        f = tmp_path / "video.mp4"
        f.write_bytes(b"\x00" * 100)
        result = _build_artifact_section((f,))
        assert "binary/large" in result

    def test_handles_missing_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "gone.json"
        result = _build_artifact_section((missing,))
        assert "not found" in result


class TestReflectionResult:
    def test_valid_creation(self) -> None:
        critique = QACritique(decision=QADecision.PASS, score=90, gate=GateName("r"), attempt=1, confidence=0.9)
        result = ReflectionResult(best_critique=critique, artifacts=(), attempts=1)
        assert result.attempts == 1
        assert not result.escalation_needed

    def test_invalid_attempts_raises(self) -> None:
        critique = QACritique(decision=QADecision.PASS, score=90, gate=GateName("r"), attempt=1, confidence=0.9)
        with pytest.raises(ValueError, match="attempts must be >= 1"):
            ReflectionResult(best_critique=critique, artifacts=(), attempts=0)
