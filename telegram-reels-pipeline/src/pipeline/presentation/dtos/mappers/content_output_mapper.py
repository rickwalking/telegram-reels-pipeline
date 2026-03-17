"""Mapper: ContentOutputDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO


def map_content_dto_to_event_payload(dto: ContentOutputDTO) -> dict[str, object]:
    """Extract ContentOutputDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "description_options": list(dto.description_options),
        "hashtag_sets": [list(hashtag_set) for hashtag_set in dto.hashtag_sets],
        "music_suggestions": list(dto.music_suggestions),
    }
