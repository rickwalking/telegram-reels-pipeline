"""DTO for Layout Detective agent stage output."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class FacePositionItemDTO(BaseModel):
    """Per-frame face bounding box and detection confidence."""

    model_config = ConfigDict(strict=True, extra="forbid")

    frame_index: int
    face_x: int
    face_y: int
    face_width: int
    face_height: int
    confidence: float


class LayoutAnalysisOutputDTO(BaseStageOutputDTO):
    """Output from the Layout Detective agent stage with face positions and framing recommendation."""

    model_config = ConfigDict(strict=True, extra="forbid")

    layout_classification: str
    face_positions: list[FacePositionItemDTO]
    framing_style_recommendation: str
