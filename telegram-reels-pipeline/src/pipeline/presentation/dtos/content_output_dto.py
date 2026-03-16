"""DTO for Content Creator agent stage output."""

from __future__ import annotations

from pydantic import ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class ContentOutputDTO(BaseStageOutputDTO):
    """Output from the Content Creator agent stage with descriptions, hashtags, and music."""

    model_config = ConfigDict(strict=True, extra="forbid")

    description_options: list[str]
    hashtag_sets: list[list[str]]
    music_suggestions: list[str]
