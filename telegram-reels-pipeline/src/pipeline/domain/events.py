"""Domain event models for event-sourced pipeline state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True)
class PipelineStateEvent:
    """A single immutable event in the pipeline event stream."""

    event_id: str
    pipeline_run_id: str
    event_type: str
    timestamp: str
    stage_name: str = ""
    payload: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not self.timestamp:
            raise ValueError("timestamp must not be empty")
        if not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True)
class RunStateProjection:
    """Materialized view of a pipeline run derived from replaying events."""

    pipeline_run_id: str
    current_stage: str
    execution_status: str = "running"
    stages_completed: tuple[str, ...] = ()
    last_event_id: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.current_stage:
            raise ValueError("current_stage must not be empty")


@dataclass(frozen=True)
class CreatePipelineRunCommand:
    """Command to initiate a new pipeline run."""

    pipeline_run_id: str
    youtube_url: str
    topic_focus: str = ""

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")
