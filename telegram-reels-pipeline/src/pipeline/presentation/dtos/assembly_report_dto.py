"""DTO for Assembly agent stage output — final reel assembly report."""

from __future__ import annotations

from pydantic import ConfigDict

from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO


class AssemblyReportDTO(BaseStageOutputDTO):
    """Output from the Assembly agent stage with final reel path and quality metrics."""

    model_config = ConfigDict(strict=True, extra="forbid")

    final_reel_path: str
    total_duration_seconds: float
    segment_count: int
    quality_score: float
