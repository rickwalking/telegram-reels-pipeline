"""ReflectionLoop — Generator-Critic QA with retry and best-of-three selection."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pipeline.domain.enums import QADecision
from pipeline.domain.errors import QAError
from pipeline.domain.models import AgentRequest, AgentResult, QACritique, ReflectionResult
from pipeline.domain.transitions import MAX_QA_ATTEMPTS
from pipeline.domain.types import GateName

if TYPE_CHECKING:
    from pipeline.domain.ports import AgentExecutionPort, ModelDispatchPort

logger = logging.getLogger(__name__)

# Minimum score threshold — below this, escalation is triggered even for best-of-three
MIN_SCORE_THRESHOLD: int = 40

# QA model role identifier for ModelDispatchPort
QA_ROLE: str = "qa_evaluator"


class ReflectionLoop:
    """Evaluate agent outputs against QA gate criteria with automatic rework.

    Drives the Generator-Critic pattern:
    1. Agent produces artifacts (generator)
    2. QA model evaluates against criteria (critic)
    3. On REWORK, agent retries with prescriptive fixes
    4. After MAX_QA_ATTEMPTS, best-of-three selects highest score
    5. If best score < min_score_threshold, escalation is signalled
    """

    def __init__(
        self,
        agent_port: AgentExecutionPort,
        model_port: ModelDispatchPort,
        min_score_threshold: int = MIN_SCORE_THRESHOLD,
    ) -> None:
        self._agent_port = agent_port
        self._model_port = model_port
        self._min_score_threshold = min_score_threshold

    async def evaluate(
        self,
        artifacts: tuple[Path, ...],
        gate: GateName,
        gate_criteria: str,
        attempt: int,
        evaluation_context: Mapping[str, str] | None = None,
    ) -> QACritique:
        """Evaluate artifacts against QA gate criteria via the model dispatch port.

        Inlines text artifact contents so the QA model can evaluate without tool access.
        If evaluation_context is provided, it is included in the prompt so the QA model
        knows about conditional criteria (e.g. publishing_language for publishing assets).
        Raises QAError if the model response cannot be parsed into a valid QACritique.
        """
        artifacts_text = _build_artifact_section(artifacts)

        context_section = ""
        if evaluation_context:
            context_lines = "\n".join(f"{k}: {v}" for k, v in evaluation_context.items())
            context_section = f"### Evaluation Context\n\n{context_lines}\n\n"

        prompt = (
            f"## QA Gate Evaluation: {gate}\n\n"
            f"### Gate Criteria\n\n{gate_criteria}\n\n"
            f"{context_section}"
            f"### Artifacts to Evaluate\n\n{artifacts_text}\n\n"
            f"### Attempt: {attempt}\n\n"
            "Evaluate the artifacts against the gate criteria. "
            "Respond with ONLY a JSON object matching this exact schema:\n"
            '{"decision": "PASS|REWORK|FAIL", "score": 0-100, "gate": "<gate_name>", '
            '"attempt": <int>, "blockers": [{"severity": "...", "description": "..."}], '
            '"prescriptive_fixes": ["exact fix instruction"], "confidence": 0.0-1.0}'
        )

        raw_response: str = await self._model_port.dispatch(QA_ROLE, prompt)

        return _parse_critique(raw_response, gate, attempt)

    async def run(
        self,
        request: AgentRequest,
        gate: GateName,
        gate_criteria: str,
    ) -> ReflectionResult:
        """Execute the full reflection loop: agent → QA → rework cycle.

        Returns ReflectionResult with the best critique and whether escalation is needed.
        """
        attempts: list[tuple[QACritique, AgentResult]] = []
        current_request = request

        # Forward non-empty elicitation context entries to QA evaluation
        eval_ctx = {k: v for k, v in request.elicitation_context.items() if v}
        evaluation_context: Mapping[str, str] | None = eval_ctx if eval_ctx else None

        for attempt_num in range(1, MAX_QA_ATTEMPTS + 1):
            # Execute the agent
            result: AgentResult = await self._agent_port.execute(current_request)

            # Evaluate artifacts
            critique = await self.evaluate(
                result.artifacts, gate, gate_criteria, attempt_num, evaluation_context=evaluation_context
            )
            attempts.append((critique, result))

            logger.info(
                "QA gate %s attempt %d: %s (score=%d)",
                gate,
                attempt_num,
                critique.decision.value,
                critique.score,
            )

            if critique.decision == QADecision.PASS:
                return ReflectionResult(
                    best_critique=critique,
                    artifacts=result.artifacts,
                    attempts=attempt_num,
                    escalation_needed=False,
                )

            if critique.decision == QADecision.FAIL:
                # FAIL means no rework possible — skip to best-of-three
                break

            # REWORK — build new request with prescriptive fixes as attempt history
            if attempt_num < MAX_QA_ATTEMPTS:
                feedback_entry = {
                    "attempt": str(attempt_num),
                    "decision": critique.decision.value,
                    "score": str(critique.score),
                    "prescriptive_fixes": "; ".join(critique.prescriptive_fixes),
                    "blockers": "; ".join(b.get("description", "") for b in critique.blockers),
                }
                current_request = AgentRequest(
                    stage=request.stage,
                    step_file=request.step_file,
                    agent_definition=request.agent_definition,
                    prior_artifacts=request.prior_artifacts,
                    elicitation_context=request.elicitation_context,
                    attempt_history=request.attempt_history + (feedback_entry,),
                )

        # Best-of-three selection
        best_critique, best_result = select_best(attempts)

        escalation_needed = best_critique.score < self._min_score_threshold

        logger.info(
            "QA gate %s: best-of-%d selected (score=%d, escalation=%s)",
            gate,
            len(attempts),
            best_critique.score,
            escalation_needed,
        )

        return ReflectionResult(
            best_critique=best_critique,
            artifacts=best_result.artifacts,
            attempts=len(attempts),
            escalation_needed=escalation_needed,
        )


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    """Extract the first JSON object from a raw string.

    Handles markdown code fences, trailing text, and mixed content.
    Returns the parsed dict, or None if no valid JSON object found.
    """
    cleaned = raw.strip()

    # Strategy 1: Strip markdown code fences and try direct parse
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        candidate = "\n".join(lines).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # Strategy 2: Direct parse
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Strategy 3: raw_decode from first { to handle JSON + trailing text
    brace_idx = cleaned.find("{")
    if brace_idx >= 0:
        decoder = json.JSONDecoder()
        try:
            data, _ = decoder.raw_decode(cleaned, brace_idx)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    return None


_TEXT_SUFFIXES: frozenset[str] = frozenset({".md", ".json", ".txt", ".yaml", ".yml"})
_MAX_INLINE_BYTES: int = 50_000


def _build_artifact_section(artifacts: tuple[Path, ...]) -> str:
    """Build a text block with inlined artifact contents for QA evaluation.

    Inlines text files under 50 KB; shows only metadata for binary/large files.
    Returns a placeholder when no artifacts are present.
    """
    if not artifacts:
        return "(No artifacts produced — agent did not write any output files)"

    parts: list[str] = []
    for path in artifacts:
        if not path.exists():
            parts.append(f"#### {path.name}\n\n(file not found)")
            continue
        size = path.stat().st_size
        if path.suffix in _TEXT_SUFFIXES and size <= _MAX_INLINE_BYTES:
            content = path.read_text(errors="replace")
            parts.append(f"#### {path.name}\n\n~~~~\n{content}\n~~~~")
        else:
            parts.append(f"#### {path.name} (binary/large — {size} bytes)")
    return "\n\n".join(parts)


def select_best(
    attempts: list[tuple[QACritique, AgentResult]],
) -> tuple[QACritique, AgentResult]:
    """Select the highest-scoring attempt from a list of (critique, result) pairs.

    Raises QAError if the attempts list is empty.
    """
    if not attempts:
        raise QAError("No QA attempts to select from")
    return max(attempts, key=lambda pair: pair[0].score)


def _parse_critique(raw: str, gate: GateName, attempt: int) -> QACritique:
    """Parse a raw JSON string into a QACritique domain model.

    Uses multiple strategies to extract JSON from the response:
    1. Direct parse after stripping markdown fences
    2. raw_decode from first { to handle JSON with trailing text
    3. Search for JSON in markdown fences

    Raises QAError if parsing fails or the response is invalid.
    """
    data = _extract_json_object(raw)
    if data is None:
        raise QAError(f"QA response contains no valid JSON object (response length: {len(raw)})")

    if not isinstance(data, dict):
        raise QAError(f"QA response is not a JSON object, got {type(data).__name__}")

    try:
        decision = QADecision(data["decision"])
    except (KeyError, ValueError) as exc:
        raise QAError(f"Invalid or missing 'decision' in QA response: {exc}") from exc

    try:
        score = int(data.get("score", 0))
        confidence = float(data.get("confidence", 0.0))
        blockers_raw = data.get("blockers", [])
        blockers = tuple({str(k): str(v) for k, v in b.items()} for b in blockers_raw if isinstance(b, dict))
        fixes = tuple(str(f) for f in data.get("prescriptive_fixes", []))
    except (TypeError, ValueError) as exc:
        raise QAError(f"Invalid field values in QA response: {exc}") from exc

    return QACritique(
        decision=decision,
        score=score,
        gate=gate,
        attempt=attempt,
        blockers=blockers,
        prescriptive_fixes=fixes,
        confidence=confidence,
    )
