"""Registry mapping stage names to their Pydantic DTO classes for validation."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO
from pipeline.presentation.dtos.base_stage_output_dto import BaseStageOutputDTO
from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO
from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO
from pipeline.presentation.dtos.layout_analysis_output_dto import LayoutAnalysisOutputDTO
from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO
from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO
from pipeline.presentation.dtos.transcript_output_dto import TranscriptOutputDTO

STAGE_OUTPUT_DTO_REGISTRY: Mapping[str, type[BaseStageOutputDTO]] = MappingProxyType({
    "router": RouterOutputDTO,
    "research": ResearchOutputDTO,
    "transcript": TranscriptOutputDTO,
    "content": ContentOutputDTO,
    "layout_detective": LayoutAnalysisOutputDTO,
    "ffmpeg_engineer": FfmpegEncodingPlanDTO,
    "assembly": AssemblyReportDTO,
})


def get_dto_class_for_stage(stage_name: str) -> type[BaseStageOutputDTO]:
    """Look up the DTO class for a given stage name.

    Raises ValueError for unknown stages.
    """
    dto_class = STAGE_OUTPUT_DTO_REGISTRY.get(stage_name)
    if dto_class is None:
        valid_stages = ", ".join(STAGE_OUTPUT_DTO_REGISTRY.keys())
        raise ValueError(f"Unknown stage: '{stage_name}'. Valid stages: {valid_stages}")
    return dto_class
