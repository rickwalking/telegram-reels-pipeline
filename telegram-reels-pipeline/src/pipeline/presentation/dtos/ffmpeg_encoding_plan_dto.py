"""DTO for FFmpeg Engineer agent stage output — encoding plan with video segments."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class VideoSegmentDTO(BaseModel):
    """A single video segment with crop coordinates and framing style."""

    model_config = ConfigDict(strict=True, extra="forbid")

    start_seconds: float
    end_seconds: float
    crop_x: int
    crop_y: int
    crop_width: int
    crop_height: int
    framing_style: str


class FfmpegEncodingPlanDTO(BaseStageOutputDTO):
    """Output from the FFmpeg Engineer agent stage with encoding plan and segment list."""

    model_config = ConfigDict(strict=True, extra="forbid")

    segments: list[VideoSegmentDTO]
    codec: str = "libx264"
    bitrate: str = "4M"
    thread_count: int = 2
    output_resolution: str = "1080x1920"
