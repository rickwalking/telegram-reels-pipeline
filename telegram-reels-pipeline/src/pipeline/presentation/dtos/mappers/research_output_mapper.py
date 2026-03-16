"""Mapper: ResearchOutputDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO


def map_research_dto_to_event_payload(dto: ResearchOutputDTO) -> dict[str, object]:
    """Extract ResearchOutputDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "episode_title": dto.episode_title,
        "channel_name": dto.channel_name,
        "episode_duration_seconds": dto.episode_duration_seconds,
        "context_summary": dto.context_summary,
        "key_topics": list(dto.key_topics),
    }
