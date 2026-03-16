"""Mapper: RouterOutputDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO


def map_router_dto_to_event_payload(dto: RouterOutputDTO) -> dict[str, object]:
    """Extract RouterOutputDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "tier": dto.tier,
        "topic_focus": dto.topic_focus,
        "elicitation_answers": dict(dto.elicitation_answers),
        "style_preference": dto.style_preference,
    }
