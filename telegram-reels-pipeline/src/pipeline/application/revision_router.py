"""RevisionRouter — classify user revision requests and build RevisionRequest."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from pipeline.domain.enums import RevisionType
from pipeline.domain.models import RevisionRequest
from pipeline.domain.types import RunId

if TYPE_CHECKING:
    from pipeline.domain.ports import MessagingPort, ModelDispatchPort

logger = logging.getLogger(__name__)

# Minimum confidence threshold for accepting a classification without clarification
_CONFIDENCE_THRESHOLD: float = 0.7

# Mapping from AI output strings to enum values
_TYPE_MAP: dict[str, RevisionType] = {
    "extend_moment": RevisionType.EXTEND_MOMENT,
    "fix_framing": RevisionType.FIX_FRAMING,
    "different_moment": RevisionType.DIFFERENT_MOMENT,
    "add_context": RevisionType.ADD_CONTEXT,
}


def parse_revision_classification(raw: str) -> tuple[RevisionType, float]:
    """Parse JSON output from the AI revision classifier.

    Returns (revision_type, confidence). Raises ValueError on invalid input.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in revision classification: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object for revision classification")

    raw_type = data.get("revision_type", "")
    if not isinstance(raw_type, str) or raw_type not in _TYPE_MAP:
        valid = ", ".join(sorted(_TYPE_MAP))
        raise ValueError(f"Unknown revision_type '{raw_type}'. Valid types: {valid}")

    confidence = data.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        raise ValueError(f"confidence must be a number, got {type(confidence).__name__}")
    confidence = float(confidence)
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"confidence must be 0.0-1.0, got {confidence}")

    return _TYPE_MAP[raw_type], confidence


def parse_timestamp_hint(raw: str) -> float | None:
    """Extract an optional timestamp hint from the AI analysis. Returns seconds or None."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    hint = data.get("timestamp_hint")
    if hint is None:
        return None
    try:
        return float(hint)
    except (TypeError, ValueError):
        return None


def parse_extra_seconds(raw: str) -> float:
    """Extract extra seconds from the AI analysis. Defaults to 0.0."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0.0

    extra = data.get("extra_seconds", 0.0)
    try:
        val = float(extra)
        return max(val, 0.0)
    except (TypeError, ValueError):
        return 0.0


class RevisionRouter:
    """Classify user revision messages and route to the appropriate handler.

    Uses the ModelDispatchPort to have an AI agent classify the revision type.
    Falls back to asking clarifying questions when confidence is below threshold.
    """

    def __init__(
        self,
        model_dispatch: ModelDispatchPort,
        messaging: MessagingPort | None = None,
    ) -> None:
        self._model_dispatch = model_dispatch
        self._messaging = messaging

    async def classify(self, user_message: str, run_id: RunId) -> RevisionRequest:
        """Classify a user revision message into a structured RevisionRequest.

        Steps:
        1. Send message to AI for classification
        2. If confidence >= threshold, accept classification
        3. If confidence < threshold and messaging available, ask clarifying question
        4. Build and return RevisionRequest

        Raises ValueError if classification fails after clarification attempt.
        """
        prompt = self._build_classification_prompt(user_message)
        raw = await self._model_dispatch.dispatch("revision_classifier", prompt)

        revision_type, confidence = parse_revision_classification(raw)
        logger.info("Classified revision as %s (confidence=%.2f)", revision_type.value, confidence)

        if confidence < _CONFIDENCE_THRESHOLD and self._messaging is not None:
            revision_type = await self._clarify(revision_type)

        timestamp_hint = parse_timestamp_hint(raw)
        extra_seconds = parse_extra_seconds(raw)

        return RevisionRequest(
            revision_type=revision_type,
            run_id=run_id,
            user_message=user_message,
            timestamp_hint=timestamp_hint,
            extra_seconds=extra_seconds,
        )

    async def _clarify(self, suggested: RevisionType) -> RevisionType:
        """Ask user to confirm or correct the classification."""
        assert self._messaging is not None

        options = "\n".join(
            f"  {i+1}. {rt.value.replace('_', ' ').title()}"
            for i, rt in enumerate(RevisionType)
        )
        question = (
            f"I think you want: {suggested.value.replace('_', ' ').title()}\n"
            f"Is that correct? Reply with a number to choose:\n{options}\n"
            f"Or reply 'yes' to confirm."
        )
        response = await self._messaging.ask_user(question)
        response = response.strip().lower()

        if response in ("yes", "y", ""):
            return suggested

        try:
            idx = int(response) - 1
            types = list(RevisionType)
            if 0 <= idx < len(types):
                return types[idx]
        except ValueError:
            pass

        # Try matching by name
        for rt in RevisionType:
            if response in rt.value or rt.value.replace("_", " ") in response:
                return rt

        logger.warning("Could not parse clarification response: %s — using suggested type", response)
        return suggested

    @staticmethod
    def _build_classification_prompt(user_message: str) -> str:
        """Build the prompt for the AI revision classifier."""
        return (
            "Classify this user revision request into one of these types:\n"
            "- extend_moment: User wants more seconds before/after the current clip\n"
            "- fix_framing: User wants to correct camera framing on a segment\n"
            "- different_moment: User wants a completely different clip from the episode\n"
            "- add_context: User wants to widen the clip to include surrounding context\n\n"
            f"User message: {user_message}\n\n"
            "Respond with JSON: {\"revision_type\": \"...\", \"confidence\": 0.0-1.0, "
            "\"reasoning\": \"...\", \"extra_seconds\": 0, \"timestamp_hint\": null}"
        )
