"""Domain event models — immutable records of state changes in the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class PipelineStateEvent:
    """Immutable event representing a state change in the pipeline."""

    event_id: str
    pipeline_run_id: str
    event_type: str
    stage_name: str
    payload_data: Mapping[str, object]
    created_at: str

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not self.created_at:
            raise ValueError("created_at must not be empty")
        if not isinstance(self.payload_data, MappingProxyType):
            object.__setattr__(self, "payload_data", MappingProxyType(dict(self.payload_data)))


@dataclass(frozen=True)
class RunStateProjection:
    """Projected current state of a pipeline run, derived from events."""

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
        if self.current_attempt_count < 0:
            raise ValueError("current_attempt_count must not be negative")


@dataclass(frozen=True)
class CreatePipelineRunCommand:
    """Command to create a new pipeline run."""

    youtube_url: str
    topic_focus: str
    trigger_source: str
    client_identifier: str

    def __post_init__(self) -> None:
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")
        if not self.trigger_source:
            raise ValueError("trigger_source must not be empty")
