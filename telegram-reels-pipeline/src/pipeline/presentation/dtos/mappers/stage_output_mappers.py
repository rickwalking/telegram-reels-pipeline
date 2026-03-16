"""Backward-compatibility re-exports for stage output mapper functions.

Each mapper now lives in its own dedicated module.  This module re-exports all
seven functions so that existing import sites continue to work without changes.
"""

from __future__ import annotations

from pipeline.presentation.dtos.mappers.assembly_report_mapper import (
    map_assembly_report_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.content_output_mapper import (
    map_content_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.ffmpeg_encoding_plan_mapper import (
    map_ffmpeg_encoding_plan_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.layout_analysis_output_mapper import (
    map_layout_analysis_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.research_output_mapper import (
    map_research_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.router_output_mapper import (
    map_router_dto_to_event_payload,
)
from pipeline.presentation.dtos.mappers.transcript_output_mapper import (
    map_transcript_dto_to_event_payload,
)

__all__ = [
    "map_router_dto_to_event_payload",
    "map_research_dto_to_event_payload",
    "map_transcript_dto_to_event_payload",
    "map_content_dto_to_event_payload",
    "map_layout_analysis_dto_to_event_payload",
    "map_ffmpeg_encoding_plan_dto_to_event_payload",
    "map_assembly_report_dto_to_event_payload",
]
