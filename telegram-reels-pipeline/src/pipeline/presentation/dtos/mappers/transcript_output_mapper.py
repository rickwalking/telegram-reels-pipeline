"""Mapper: TranscriptOutputDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.transcript_output_dto import TranscriptOutputDTO


def map_transcript_dto_to_event_payload(dto: TranscriptOutputDTO) -> dict[str, object]:
    """Extract TranscriptOutputDTO fields into a flat event payload dict."""
    moments_payload: list[dict[str, object]] = [
        {
            "moment_start_seconds": moment.moment_start_seconds,
            "moment_end_seconds": moment.moment_end_seconds,
            "selected_quote": moment.selected_quote,
            "narrative_role": moment.narrative_role,
            "selection_reasoning": moment.selection_reasoning,
        }
        for moment in dto.moments
    ]
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "moments": moments_payload,
    }
