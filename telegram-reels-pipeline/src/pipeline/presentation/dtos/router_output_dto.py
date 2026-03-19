"""DTO for Router agent stage output."""

from __future__ import annotations

from pydantic import ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class RouterOutputDTO(BaseStageOutputDTO):
    """Output from the Router agent stage containing routing decision and topic focus."""

    model_config = ConfigDict(strict=True, extra="forbid")

    tier: str
    topic_focus: str
    elicitation_answers: dict[str, str]
    style_preference: str = "auto"
