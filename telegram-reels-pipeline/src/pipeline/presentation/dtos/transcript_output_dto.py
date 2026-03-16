"""DTO for Transcript agent stage output including moment selections."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class MomentSelectionItemDTO(BaseModel):
    """A single selected transcript moment with timing, quote, and narrative role."""

    model_config = ConfigDict(strict=True, extra="forbid")

    moment_start_seconds: float
    moment_end_seconds: float
    selected_quote: str
    narrative_role: str
    selection_reasoning: str

    @field_validator("moment_end_seconds")
    @classmethod
    def end_must_be_after_start(cls, value: float, info: ValidationInfo) -> float:
        """Ensure moment_end_seconds is strictly greater than moment_start_seconds."""
        if info.data and "moment_start_seconds" in info.data and value <= info.data["moment_start_seconds"]:
            raise ValueError("moment_end_seconds must be greater than moment_start_seconds")
        return value


class TranscriptOutputDTO(BaseStageOutputDTO):
    """Output from the Transcript agent stage containing selected moments with narrative roles."""

    model_config = ConfigDict(strict=True, extra="forbid")

    moments: list[MomentSelectionItemDTO]
