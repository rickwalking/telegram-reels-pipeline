"""TelegramNotifier — send pipeline status messages via Telegram on stage transitions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pipeline.domain.models import PipelineEvent

if TYPE_CHECKING:
    from pipeline.domain.ports import MessagingPort

logger = logging.getLogger(__name__)

# Events that trigger a Telegram notification
NOTIFY_EVENTS: frozenset[str] = frozenset(
    {
        "pipeline.stage_entered",
        "pipeline.stage_completed",
        "pipeline.run_completed",
        "pipeline.run_failed",
        "qa.gate_passed",
        "qa.gate_failed",
        "error.escalated",
    }
)

# Total number of processing stages for progress display
TOTAL_STAGES: int = 8


class TelegramNotifier:
    """Send status messages to the user via Telegram on pipeline events.

    Only triggers on events in NOTIFY_EVENTS.
    """

    def __init__(self, messaging: MessagingPort) -> None:
        self._messaging = messaging

    async def __call__(self, event: PipelineEvent) -> None:
        """Send a Telegram notification for relevant pipeline events."""
        if event.event_name not in NOTIFY_EVENTS:
            return

        message = _format_message(event)
        await self._messaging.notify_user(message)

    @staticmethod
    def format_message(event: PipelineEvent) -> str:
        """Public access to message formatting for testing."""
        return _format_message(event)


def _format_message(event: PipelineEvent) -> str:
    """Format a PipelineEvent into a user-friendly Telegram message."""
    stage_name = event.stage.value if event.stage is not None else "unknown"
    stage_num = event.data.get("stage_number", "?")

    if event.event_name == "pipeline.stage_entered":
        return f"Processing stage {stage_num}/{TOTAL_STAGES}: {stage_name}..."

    if event.event_name == "pipeline.stage_completed":
        return f"Stage {stage_name} completed."

    if event.event_name == "pipeline.run_completed":
        return "Pipeline completed successfully!"

    if event.event_name == "pipeline.run_failed":
        reason = event.data.get("reason", "unknown error")
        return f"Pipeline failed: {reason}"

    if event.event_name == "qa.gate_passed":
        score = event.data.get("score", "?")
        return f"QA gate {stage_name}: PASS (score: {score}/100)"

    if event.event_name == "qa.gate_failed":
        score = event.data.get("score", "?")
        return f"QA gate {stage_name}: FAIL (score: {score}/100)"

    if event.event_name == "error.escalated":
        description = event.data.get("description", "Unknown issue")
        return f"Pipeline needs help: {description}"

    return f"Pipeline event: {event.event_name}"
