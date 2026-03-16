"""Pure mapper functions — convert stage output DTOs to event payload dicts.

Each function extracts DTO fields into a flat ``dict[str, object]`` suitable
for inclusion as the ``payload_data`` of a ``PipelineStateEvent``.  All
functions are side-effect free and accept exactly one DTO argument.
"""

from __future__ import annotations

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO
from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO
from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO
from pipeline.presentation.dtos.layout_analysis_output_dto import LayoutAnalysisOutputDTO
from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO
from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO
from pipeline.presentation.dtos.transcript_output_dto import TranscriptOutputDTO


def map_router_dto_to_event_payload(dto: RouterOutputDTO) -> dict[str, object]:
    """Extract RouterOutputDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "tier": dto.tier,
        "topic_focus": dto.topic_focus,
        "elicitation_answers": dict(dto.elicitation_answers),
        "style_preference": dto.style_preference,
    }


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


def map_transcript_dto_to_event_payload(dto: TranscriptOutputDTO) -> dict[str, object]:
    """Extract TranscriptOutputDTO fields into a flat event payload dict."""
    moments_payload: list[dict[str, object]] = [
        {
            "moment_start_seconds": moment.moment_start_seconds,
            "moment_end_seconds": moment.moment_end_seconds,
            "selected_quote": moment.selected_quote,
            "narrative_role": moment.narrative_role,
            "selection_reasoning": moment.selection_reasoning,
        }
        for moment in dto.moments
    ]
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "moments": moments_payload,
    }


def map_content_dto_to_event_payload(dto: ContentOutputDTO) -> dict[str, object]:
    """Extract ContentOutputDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "description_options": list(dto.description_options),
        "hashtag_sets": [list(hashtag_set) for hashtag_set in dto.hashtag_sets],
        "music_suggestions": list(dto.music_suggestions),
    }


def map_layout_analysis_dto_to_event_payload(dto: LayoutAnalysisOutputDTO) -> dict[str, object]:
    """Extract LayoutAnalysisOutputDTO fields into a flat event payload dict."""
    face_positions_payload: list[dict[str, object]] = [
        {
            "frame_index": face.frame_index,
            "face_x": face.face_x,
            "face_y": face.face_y,
            "face_width": face.face_width,
            "face_height": face.face_height,
            "confidence": face.confidence,
        }
        for face in dto.face_positions
    ]
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "layout_classification": dto.layout_classification,
        "face_positions": face_positions_payload,
        "framing_style_recommendation": dto.framing_style_recommendation,
    }


def map_ffmpeg_encoding_plan_dto_to_event_payload(dto: FfmpegEncodingPlanDTO) -> dict[str, object]:
    """Extract FfmpegEncodingPlanDTO fields into a flat event payload dict."""
    segments_payload: list[dict[str, object]] = [
        {
            "start_seconds": segment.start_seconds,
            "end_seconds": segment.end_seconds,
            "crop_x": segment.crop_x,
            "crop_y": segment.crop_y,
            "crop_width": segment.crop_width,
            "crop_height": segment.crop_height,
            "framing_style": segment.framing_style,
        }
        for segment in dto.segments
    ]
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "segments": segments_payload,
        "codec": dto.codec,
        "bitrate": dto.bitrate,
        "thread_count": dto.thread_count,
        "output_resolution": dto.output_resolution,
    }


def map_assembly_report_dto_to_event_payload(dto: AssemblyReportDTO) -> dict[str, object]:
    """Extract AssemblyReportDTO fields into a flat event payload dict."""
    return {
        "pipeline_run_id": dto.pipeline_run_id,
        "stage_name": dto.stage_name,
        "generated_at": dto.generated_at,
        "final_reel_path": dto.final_reel_path,
        "total_duration_seconds": dto.total_duration_seconds,
        "segment_count": dto.segment_count,
        "quality_score": dto.quality_score,
    }
