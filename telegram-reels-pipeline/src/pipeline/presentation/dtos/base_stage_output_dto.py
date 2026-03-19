"""Base DTO for all agent stage outputs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BaseStageOutputDTO(BaseModel):
    """Common fields shared by all agent stage output DTOs."""

    model_config = ConfigDict(strict=True, extra="forbid")

    pipeline_run_id: str
    stage_name: str
    generated_at: str
