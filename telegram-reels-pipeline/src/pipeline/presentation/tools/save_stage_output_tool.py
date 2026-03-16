"""MCP tool factory: save_stage_output — validate and persist an agent stage output."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from pipeline.application.use_cases.save_stage_output_use_case import (
    SaveStageOutputCommand,
    SaveStageOutputUseCase,
)
from pipeline.presentation.dtos.stage_output_dto_registry import get_dto_class_for_stage
from pipeline.presentation.tools.format_error_response import format_error_response
from pipeline.presentation.tools.format_success_response import format_success_response

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from pipeline.presentation.tools.tool_registry import ToolRegistryDependencies


def register_save_stage_output_tool(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register the save_stage_output tool onto the given MCP server."""
    use_case = SaveStageOutputUseCase(
        event_store_port=dependencies.event_store_port,
        state_store_port=dependencies.state_store_port,
    )

    @mcp_server.tool()
    def save_stage_output(
        pipeline_run_id: str,
        stage_name: str,
        output_payload_json: str,
    ) -> str:
        """Validate and persist a completed stage output as a pipeline event.

        Args:
            pipeline_run_id: Unique identifier of the pipeline run.
            stage_name: Name of the completed stage (e.g. ``router``, ``research``).
            output_payload_json: JSON string matching the stage's DTO schema.

        Returns:
            JSON string with ``status`` ``"success"`` and ``event_id``,
            or an error JSON string on validation or parse failure.
        """
        return asyncio.run(_execute_save_stage_output(use_case, pipeline_run_id, stage_name, output_payload_json))


async def _execute_save_stage_output(
    use_case: SaveStageOutputUseCase,
    pipeline_run_id: str,
    stage_name: str,
    output_payload_json: str,
) -> str:
    """Async implementation for save_stage_output — parse, validate, and persist."""
    raw_payload = _parse_json_payload(output_payload_json)
    if isinstance(raw_payload, str):
        return raw_payload

    dto_class = _resolve_dto_class(stage_name)
    if isinstance(dto_class, str):
        return dto_class

    validated_payload = _validate_dto(dto_class, raw_payload)
    if isinstance(validated_payload, str):
        return validated_payload

    command = SaveStageOutputCommand(
        pipeline_run_id=pipeline_run_id,
        stage_name=stage_name,
        payload_data=validated_payload.model_dump(),
    )
    event_id = await use_case.execute(command)
    return format_success_response({"event_id": event_id, "stage_name": stage_name})


def _parse_json_payload(output_payload_json: str) -> dict[str, object] | str:
    """Parse the JSON string into a dict. Return an error response string on failure."""
    try:
        parsed = json.loads(output_payload_json)
        if not isinstance(parsed, dict):
            return format_error_response("validation_error", "Payload must be a JSON object.")
        return parsed
    except json.JSONDecodeError as exc:
        return format_error_response("invalid_json", f"Could not parse JSON payload: {exc}")


def _resolve_dto_class(stage_name: str) -> object | str:
    """Look up the DTO class for a stage name. Return an error response string if unknown."""
    try:
        return get_dto_class_for_stage(stage_name)
    except ValueError as exc:
        return format_error_response("unknown_stage", str(exc))


def _validate_dto(dto_class: object, raw_payload: dict[str, object]) -> object | str:
    """Validate the raw payload against the DTO class. Return error response string on failure."""
    try:
        return dto_class(**raw_payload)  # type: ignore[operator]
    except ValidationError as exc:
        error_message = f"Payload failed DTO validation for this stage: {exc.error_count()} error(s). {exc}"
        return format_error_response("validation_error", error_message)
