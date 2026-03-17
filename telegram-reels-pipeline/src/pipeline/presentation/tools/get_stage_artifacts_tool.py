"""Factory for the get_stage_artifacts MCP tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.domain.event_types import STAGE_COMPLETED
from pipeline.presentation.tools.format_error_response import format_error_response
from pipeline.presentation.tools.format_success_response import format_success_response

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort


def create_get_stage_artifacts_tool(
    event_store_port: EventStorePort,
) -> object:
    """Factory that creates the get_stage_artifacts tool with injected dependencies.

    Args:
        event_store_port: Port to retrieve pipeline state events from.

    Returns:
        An async callable registered as an MCP tool.
    """

    async def get_stage_artifacts(pipeline_run_id: str, stage_name: str) -> str:
        """Retrieve artifact metadata for a completed pipeline stage.

        Returns JSON with artifact metadata from the stage_completed event payload,
        or an error if no completed events are found for the given stage.
        """
        all_events = await event_store_port.get_events_for_run(pipeline_run_id)
        stage_completed_events = [
            event
            for event in all_events
            if event.event_type == STAGE_COMPLETED and event.stage_name == stage_name
        ]
        if not stage_completed_events:
            return format_error_response(
                "not_found",
                f"No completed events found for stage '{stage_name}' in run '{pipeline_run_id}'",
            )
        latest_event = stage_completed_events[-1]
        return format_success_response(
            {
                "pipeline_run_id": pipeline_run_id,
                "stage_name": stage_name,
                "artifacts": dict(latest_event.payload_data),
            }
        )

    return get_stage_artifacts
