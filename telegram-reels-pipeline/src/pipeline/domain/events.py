"""Domain events — frozen dataclasses for event-sourced pipeline state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class PipelineStateEvent:
    """Immutable event appended to the event store for a pipeline run."""

    event_id: str
    pipeline_run_id: str
    event_type: str
    stage_name: str
    payload_data: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not isinstance(self.payload_data, MappingProxyType):
            object.__setattr__(self, "payload_data", MappingProxyType(dict(self.payload_data)))


@dataclass(frozen=True)
class RunStateProjection:
    """Materialized view of a pipeline run derived from its event stream."""

    pipeline_run_id: str
    youtube_url: str
    trigger_source: str
    current_stage: str
    execution_status: str
    current_attempt_count: int
    qa_evaluation_status: str
    completed_stages: tuple[str, ...]
    escalation_status: str
    created_at: str
    last_updated_at: str

    def __post_init__(self) -> None:
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")


@dataclass(frozen=True)
class CreatePipelineRunCommand:
    """Command to trigger a new pipeline run."""

    youtube_url: str
    topic_focus: str
    trigger_source: str

    def __post_init__(self) -> None:
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")
        if not self.trigger_source:
            raise ValueError("trigger_source must not be empty")
