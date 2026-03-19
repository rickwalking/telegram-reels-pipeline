"""Mapper: AssemblyReportDTO → event payload dict."""

from __future__ import annotations

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO


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
