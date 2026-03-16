"""Domain event models — immutable records of state changes in the pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


_REQUIRED_EVENT_FIELDS: dict[str, str] = {
    "event_id": "event_id must not be empty",
    "pipeline_run_id": "pipeline_run_id must not be empty",
    "event_type": "event_type must not be empty",
    "created_at": "created_at must not be empty",
}

_REQUIRED_PROJECTION_FIELDS: dict[str, str] = {
    "pipeline_run_id": "pipeline_run_id must not be empty",
    "youtube_url": "youtube_url must not be empty",
}

_REQUIRED_COMMAND_FIELDS: dict[str, str] = {
    "youtube_url": "youtube_url must not be empty",
    "trigger_source": "trigger_source must not be empty",
}


def _validate_required_fields(instance: object, rules: dict[str, str]) -> None:
    """Validate that required string fields are non-empty using a rules dict."""
    for field_name, error_message in rules.items():
        if not getattr(instance, field_name):
            raise ValueError(error_message)


@dataclass(frozen=True)
class PipelineStateEvent:
    """Immutable event representing a state change in the pipeline."""

    event_id: str
    pipeline_run_id: str
    event_type: str
    stage_name: str = ""
    payload_data: Mapping[str, object] = MappingProxyType({})
    created_at: str = ""

    def __post_init__(self) -> None:
        _validate_required_fields(self, _REQUIRED_EVENT_FIELDS)
        if not isinstance(self.payload_data, MappingProxyType):
            object.__setattr__(self, "payload_data", MappingProxyType(dict(self.payload_data)))


@dataclass(frozen=True)
class RunStateProjection:
    """Projected current state of a pipeline run, derived from events."""

    pipeline_run_id: str
    youtube_url: str
    trigger_source: str = ""
    current_stage: str = "router"
    execution_status: str = "pending"
    current_attempt_count: int = 0
    qa_evaluation_status: str = "pending"
    completed_stages: tuple[str, ...] = ()
    escalation_status: str = "none"
    created_at: str = ""
    last_updated_at: str = ""

    def __post_init__(self) -> None:
        _validate_required_fields(self, _REQUIRED_PROJECTION_FIELDS)
        if self.current_attempt_count < 0:
            raise ValueError("current_attempt_count must not be negative")


@dataclass(frozen=True)
class CreatePipelineRunCommand:
    """Command to create a new pipeline run."""

    youtube_url: str
    topic_focus: str = ""
    trigger_source: str = ""
    client_identifier: str = ""

    def __post_init__(self) -> None:
        _validate_required_fields(self, _REQUIRED_COMMAND_FIELDS)
