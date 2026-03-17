"""Mapper: FfmpegEncodingPlanDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO


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
