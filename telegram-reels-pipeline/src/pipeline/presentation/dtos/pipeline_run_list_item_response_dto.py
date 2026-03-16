"""Presentation DTO for pipeline run list item responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PipelineRunListItemResponseDTO(BaseModel):
    """Compact DTO for GET /api/runs list response items."""

    model_config = ConfigDict(strict=True, extra="forbid")

    pipeline_run_id: str
    youtube_url: str
    execution_status: str
    current_stage: str
    created_at: str
