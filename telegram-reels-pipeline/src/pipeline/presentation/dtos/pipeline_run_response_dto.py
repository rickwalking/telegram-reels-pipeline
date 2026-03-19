"""Presentation DTO for outbound pipeline run state responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PipelineRunResponseDTO(BaseModel):
    """Pydantic DTO for GET/POST /api/runs response payloads."""

    model_config = ConfigDict(strict=True, extra="forbid")

    pipeline_run_id: str
    youtube_url: str
    trigger_source: str
    current_stage: str
    execution_status: str
    current_attempt_count: int
    qa_evaluation_status: str
    completed_stages: list[str]
    escalation_status: str
    created_at: str
    last_updated_at: str
