"""Tests for TelegramNotifier — send pipeline status messages via Telegram."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent
from pipeline.infrastructure.listeners.telegram_notifier import (
    NOTIFY_EVENTS,
    TOTAL_STAGES,
    TelegramNotifier,
    _format_message,
)


def _make_event(
    name: str = "pipeline.stage_entered",
    stage: PipelineStage | None = PipelineStage.ROUTER,
    data: dict[str, object] | None = None,
) -> PipelineEvent:
    return PipelineEvent(
        timestamp="2026-02-10T14:30:00Z",
        event_name=name,
        stage=stage,
        data=data or {},
    )


class TestTelegramNotifier:
    async def test_sends_notification_for_stage_entered(self) -> None:
        messaging = AsyncMock()
        notifier = TelegramNotifier(messaging)
        event = _make_event("pipeline.stage_entered", data={"stage_number": 2})

        await notifier(event)

        messaging.notify_user.assert_called_once()
        msg = messaging.notify_user.call_args[0][0]
        assert "2/8" in msg
        assert "router" in msg

    async def test_ignores_non_notify_events(self) -> None:
        messaging = AsyncMock()
        notifier = TelegramNotifier(messaging)

        await notifier(_make_event("some.random.event"))

        messaging.notify_user.assert_not_called()

    async def test_sends_for_all_notify_events(self) -> None:
        messaging = AsyncMock()
        notifier = TelegramNotifier(messaging)

        for event_name in NOTIFY_EVENTS:
            messaging.reset_mock()
            await notifier(_make_event(event_name))
            messaging.notify_user.assert_called_once()


class TestFormatMessage:
    def test_stage_entered(self) -> None:
        event = _make_event("pipeline.stage_entered", data={"stage_number": 3})
        msg = _format_message(event)
        assert f"3/{TOTAL_STAGES}" in msg
        assert "router" in msg

    def test_stage_completed(self) -> None:
        event = _make_event("pipeline.stage_completed")
        msg = _format_message(event)
        assert "router" in msg
        assert "completed" in msg

    def test_run_completed(self) -> None:
        event = _make_event("pipeline.run_completed")
        msg = _format_message(event)
        assert "successfully" in msg

    def test_run_failed(self) -> None:
        event = _make_event("pipeline.run_failed", data={"reason": "timeout"})
        msg = _format_message(event)
        assert "timeout" in msg

    def test_qa_gate_passed(self) -> None:
        event = _make_event("qa.gate_passed", data={"score": 92})
        msg = _format_message(event)
        assert "PASS" in msg
        assert "92" in msg

    def test_qa_gate_failed(self) -> None:
        event = _make_event("qa.gate_failed", data={"score": 30})
        msg = _format_message(event)
        assert "FAIL" in msg
        assert "30" in msg

    def test_error_escalated(self) -> None:
        event = _make_event("error.escalated", data={"description": "Agent crashed"})
        msg = _format_message(event)
        assert "Agent crashed" in msg

    def test_unknown_event_fallback(self) -> None:
        event = _make_event("custom.unknown.event")
        # Won't be in NOTIFY_EVENTS, but _format_message still works
        msg = _format_message(event)
        assert "custom.unknown.event" in msg

    def test_none_stage_handled(self) -> None:
        event = _make_event("pipeline.stage_entered", stage=None, data={"stage_number": 1})
        msg = _format_message(event)
        assert "unknown" in msg
