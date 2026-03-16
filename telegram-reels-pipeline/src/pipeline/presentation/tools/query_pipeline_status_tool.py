"""Factory for the query_pipeline_status MCP tool."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pipeline.presentation.tools.format_error_response import format_error_response
from pipeline.presentation.tools.format_success_response import format_success_response

if TYPE_CHECKING:
    from pipeline.domain.ports.state_store_port import StateStorePort


def create_query_pipeline_status_tool(
    state_store_port: StateStorePort,
) -> object:
    """Factory that creates the query_pipeline_status tool with injected dependencies.

    Args:
        state_store_port: Port to load pipeline run projections from.

    Returns:
        An async callable registered as an MCP tool.
    """

    async def query_pipeline_status(pipeline_run_id: str) -> str:
        """Query the current state of a pipeline run.

        Returns JSON with pipeline_run_id, current_stage, execution_status,
        completed_stages, escalation_status, and current_attempt_count.
        """
        projection = await state_store_port.load_projection(pipeline_run_id)
        if projection is None:
            return format_error_response("not_found", f"Pipeline run '{pipeline_run_id}' not found")
        return format_success_response(
            {
                "pipeline_run_id": projection.pipeline_run_id,
                "current_stage": projection.current_stage,
                "execution_status": projection.execution_status,
                "completed_stages": list(projection.completed_stages),
                "escalation_status": projection.escalation_status,
                "current_attempt_count": projection.current_attempt_count,
            }
        )

    return query_pipeline_status
