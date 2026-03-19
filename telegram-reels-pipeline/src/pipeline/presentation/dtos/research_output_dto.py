"""DTO for Research agent stage output."""

from __future__ import annotations

from pydantic import ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class ResearchOutputDTO(BaseStageOutputDTO):
    """Output from the Research agent stage containing episode metadata and context."""

    model_config = ConfigDict(strict=True, extra="forbid")

    episode_title: str
    channel_name: str
    episode_duration_seconds: float
    context_summary: str
    key_topics: list[str]
