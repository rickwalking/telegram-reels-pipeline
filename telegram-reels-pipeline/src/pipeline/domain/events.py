"""Domain event models for event-sourced pipeline state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType

from pipeline.domain.enums import EscalationState, QAStatus, RunExecutionStatus, TriggerSource


@dataclass(frozen=True)
class PipelineStateEvent:
    """Immutable domain event representing a state transition in a pipeline run.

    Each event is append-only and captures exactly one state change.
    """

    event_id: str
    pipeline_run_id: str
    event_type: str
    stage_name: str = ""
    payload: Mapping[str, object] = field(default_factory=lambda: MappingProxyType({}))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate required fields and enforce immutability of payload."""
        if not self.event_id:
            raise ValueError("event_id must not be empty")
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))


@dataclass(frozen=True)
class RunStateProjection:
    """Current-state read model derived from replaying pipeline events.

    Represents the latest known state of a pipeline run for query purposes.
    """

    pipeline_run_id: str
    youtube_url: str
    trigger_source: TriggerSource = TriggerSource.CLI
    current_stage: str = "router"
    execution_status: RunExecutionStatus = RunExecutionStatus.PENDING
    current_attempt_count: int = 0
    qa_evaluation_status: QAStatus = QAStatus.PENDING
    completed_stages: tuple[str, ...] = field(default_factory=tuple)
    escalation_status: EscalationState = EscalationState.NONE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_event_id: str | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")
        if self.current_attempt_count < 0:
            raise ValueError(f"current_attempt_count must be non-negative, got {self.current_attempt_count}")
