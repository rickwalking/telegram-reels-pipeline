"""Pydantic DTOs for pipeline event API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PipelineEventItemDTO(BaseModel):
    """Single event in a list response — lightweight summary."""

    event_id: str = Field(description="Unique event identifier")
    pipeline_run_id: str = Field(description="Parent pipeline run ID")
    timestamp: str = Field(description="ISO 8601 timestamp of the event")
    event_name: str = Field(description="Dotted event name (e.g. pipeline.stage_entered)")
    stage: str | None = Field(default=None, description="Pipeline stage, if applicable")
    data: dict[str, object] = Field(
        default_factory=dict,
        description="Event payload",
    )


class PipelineEventListResponseDTO(BaseModel):
    """Paginated list of pipeline events."""

    items: list[PipelineEventItemDTO] = Field(description="Events in ascending order")
    total: int = Field(description="Total number of events for this run")
    offset: int = Field(description="Current page offset")
    limit: int = Field(description="Page size")


class PipelineEventDetailDTO(BaseModel):
    """Full event detail — identical fields to item but used for single-event endpoint."""

    event_id: str = Field(description="Unique event identifier")
    pipeline_run_id: str = Field(description="Parent pipeline run ID")
    timestamp: str = Field(description="ISO 8601 timestamp of the event")
    event_name: str = Field(description="Dotted event name")
    stage: str | None = Field(default=None, description="Pipeline stage, if applicable")
    data: dict[str, object] = Field(
        default_factory=dict,
        description="Full event payload",
    )
