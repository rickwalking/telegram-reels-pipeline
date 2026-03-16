"""Factory for the get_qa_history MCP tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.domain.event_types import QA_GATE_FAILED, QA_GATE_PASSED, QA_GATE_REWORK
from pipeline.presentation.tools.format_error_response import format_error_response
from pipeline.presentation.tools.format_success_response import format_success_response

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort


_QA_EVENT_TYPES: frozenset[str] = frozenset({QA_GATE_PASSED, QA_GATE_REWORK, QA_GATE_FAILED})


def create_get_qa_history_tool(
    event_store_port: EventStorePort,
) -> object:
    """Factory that creates the get_qa_history tool with injected dependencies.

    Args:
        event_store_port: Port to retrieve pipeline state events from.

    Returns:
        An async callable registered as an MCP tool.
    """

    async def get_qa_history(pipeline_run_id: str, stage_name: str) -> str:
        """Retrieve QA gate attempt history for a pipeline stage.

        Returns JSON with QA attempt history including event types and scores,
        or an error if no QA events are found for the given stage.
        """
        all_events = await event_store_port.get_events_for_run(pipeline_run_id)
        qa_events = [
            event
            for event in all_events
            if event.event_type in _QA_EVENT_TYPES and event.stage_name == stage_name
        ]
        if not qa_events:
            return format_error_response(
                "not_found",
                f"No QA events found for stage '{stage_name}' in run '{pipeline_run_id}'",
            )
        attempt_history = [
            {
                "event_type": event.event_type,
                "stage_name": event.stage_name,
                "created_at": event.created_at,
                "details": dict(event.payload_data),
            }
            for event in qa_events
        ]
        return format_success_response(
            {
                "pipeline_run_id": pipeline_run_id,
                "stage_name": stage_name,
                "attempt_count": len(qa_events),
                "attempt_history": attempt_history,
            }
        )

    return get_qa_history
