"""Tests for RevisionRouter — revision type classification and routing."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.revision_router import _CONFIDENCE_THRESHOLD, RevisionRouter
from pipeline.domain.enums import RevisionType
from pipeline.domain.types import RunId


def _make_ai_response(
    revision_type: str = "extend_moment",
    confidence: float = 0.95,
    extra_seconds: float = 15.0,
    timestamp_hint: float | None = None,
) -> str:
    data: dict[str, object] = {
        "revision_type": revision_type,
        "confidence": confidence,
        "reasoning": "test reasoning",
        "extra_seconds": extra_seconds,
    }
    if timestamp_hint is not None:
        data["timestamp_hint"] = timestamp_hint
    return json.dumps(data)


def _make_router(
    ai_response: str | None = None,
    messaging: MagicMock | None = None,
) -> RevisionRouter:
    model_dispatch = MagicMock()
    model_dispatch.dispatch = AsyncMock(return_value=ai_response or _make_ai_response())

    return RevisionRouter(
        model_dispatch=model_dispatch,
        messaging=messaging,
    )


class TestClassifyHighConfidence:
    async def test_extend_moment(self) -> None:
        router = _make_router(ai_response=_make_ai_response("extend_moment", 0.95))
        result = await router.classify("Include 15 more seconds", RunId("run-1"))

        assert result.revision_type == RevisionType.EXTEND_MOMENT
        assert result.run_id == RunId("run-1")
        assert result.user_message == "Include 15 more seconds"

    async def test_fix_framing(self) -> None:
        router = _make_router(ai_response=_make_ai_response("fix_framing", 0.9))
        result = await router.classify("Wrong speaker in frame", RunId("run-2"))
        assert result.revision_type == RevisionType.FIX_FRAMING

    async def test_different_moment(self) -> None:
        router = _make_router(ai_response=_make_ai_response("different_moment", 0.85, timestamp_hint=2700.0))
        result = await router.classify("Try around 45:00", RunId("run-3"))
        assert result.revision_type == RevisionType.DIFFERENT_MOMENT
        assert result.timestamp_hint == pytest.approx(2700.0)

    async def test_add_context(self) -> None:
        router = _make_router(ai_response=_make_ai_response("add_context", 0.88, extra_seconds=30.0))
        result = await router.classify("Include the setup", RunId("run-4"))
        assert result.revision_type == RevisionType.ADD_CONTEXT
        assert result.extra_seconds == pytest.approx(30.0)

    async def test_extra_seconds_preserved(self) -> None:
        router = _make_router(ai_response=_make_ai_response("extend_moment", 0.95, extra_seconds=20.0))
        result = await router.classify("More time please", RunId("run-5"))
        assert result.extra_seconds == pytest.approx(20.0)


class TestClassifyLowConfidence:
    async def test_low_confidence_with_messaging_asks_user(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(return_value="yes")

        router = _make_router(
            ai_response=_make_ai_response("extend_moment", 0.3),
            messaging=messaging,
        )
        result = await router.classify("hmm change something", RunId("run-6"))

        messaging.ask_user.assert_awaited_once()
        assert result.revision_type == RevisionType.EXTEND_MOMENT

    async def test_low_confidence_user_selects_number(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(return_value="2")

        router = _make_router(
            ai_response=_make_ai_response("extend_moment", 0.3),
            messaging=messaging,
        )
        result = await router.classify("change something", RunId("run-7"))

        # Number 2 = FIX_FRAMING (second in RevisionType enum)
        assert result.revision_type == RevisionType.FIX_FRAMING

    async def test_low_confidence_no_messaging_accepts_suggestion(self) -> None:
        router = _make_router(ai_response=_make_ai_response("fix_framing", 0.3))
        result = await router.classify("change framing", RunId("run-8"))
        assert result.revision_type == RevisionType.FIX_FRAMING

    async def test_low_confidence_user_gives_invalid_falls_back(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(return_value="banana")

        router = _make_router(
            ai_response=_make_ai_response("different_moment", 0.4),
            messaging=messaging,
        )
        result = await router.classify("try something else", RunId("run-9"))
        assert result.revision_type == RevisionType.DIFFERENT_MOMENT


class TestBuildClassificationPrompt:
    def test_includes_user_message(self) -> None:
        prompt = RevisionRouter._build_classification_prompt("Fix the framing on segment 2")
        assert "Fix the framing on segment 2" in prompt

    def test_includes_all_revision_types(self) -> None:
        prompt = RevisionRouter._build_classification_prompt("test")
        assert "extend_moment" in prompt
        assert "fix_framing" in prompt
        assert "different_moment" in prompt
        assert "add_context" in prompt


class TestConfidenceThreshold:
    def test_threshold_is_reasonable(self) -> None:
        assert 0.5 <= _CONFIDENCE_THRESHOLD <= 0.9
