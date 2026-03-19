"""Mapper: LayoutAnalysisOutputDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.layout_analysis_output_dto import LayoutAnalysisOutputDTO


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
