"""Domain models — frozen dataclasses for pipeline value objects and state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.types import GateName, RunId, SessionId


def _freeze_mapping(m: Mapping[str, Any]) -> MappingProxyType[str, Any]:
    """Wrap a mutable mapping in MappingProxyType for immutability."""
    if isinstance(m, MappingProxyType):
        return m
    return MappingProxyType(dict(m))


@dataclass(frozen=True)
class AgentRequest:
    """Input bundle for an agent execution."""

    stage: PipelineStage
    step_file: Path
    agent_definition: Path
    prior_artifacts: tuple[Path, ...] = field(default_factory=tuple)
    elicitation_context: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    attempt_history: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.elicitation_context, MappingProxyType):
            object.__setattr__(self, "elicitation_context", _freeze_mapping(self.elicitation_context))


@dataclass(frozen=True)
class AgentResult:
    """Output from a completed agent execution."""

    status: str
    artifacts: tuple[Path, ...] = field(default_factory=tuple)
    session_id: SessionId = SessionId("")
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")


@dataclass(frozen=True)
class QACritique:
    """Structured QA gate evaluation result."""

    decision: QADecision
    score: int
    gate: GateName
    attempt: int
    blockers: tuple[Mapping[str, str], ...] = field(default_factory=tuple)
    prescriptive_fixes: tuple[str, ...] = field(default_factory=tuple)
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if not 0 <= self.score <= 100:
            raise ValueError(f"score must be 0-100, got {self.score}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if self.attempt < 1:
            raise ValueError(f"attempt must be >= 1, got {self.attempt}")


@dataclass(frozen=True)
class CropRegion:
    """Video crop coordinates for a layout strategy."""

    x: int
    y: int
    width: int
    height: int
    layout_name: str = ""

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError(f"x and y must be non-negative, got ({self.x}, {self.y})")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"width and height must be positive, got ({self.width}, {self.height})")


@dataclass(frozen=True)
class VideoMetadata:
    """YouTube video metadata extracted via yt-dlp."""

    title: str
    duration_seconds: float
    channel: str
    publish_date: str
    description: str
    url: str

    def __post_init__(self) -> None:
        if self.duration_seconds <= 0:
            raise ValueError(f"duration_seconds must be positive, got {self.duration_seconds}")
        if not self.url:
            raise ValueError("url must not be empty")


@dataclass(frozen=True)
class QueueItem:
    """A pipeline request waiting in the FIFO queue."""

    url: str
    telegram_update_id: int
    queued_at: datetime
    topic_focus: str | None = None

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("url must not be empty")


@dataclass(frozen=True)
class RunState:
    """Complete pipeline run state persisted as frontmatter in run.md."""

    run_id: RunId
    youtube_url: str
    current_stage: PipelineStage
    current_attempt: int = 1
    qa_status: QAStatus = QAStatus.PENDING
    stages_completed: tuple[str, ...] = field(default_factory=tuple)
    escalation_state: EscalationState = EscalationState.NONE
    best_of_three_overrides: tuple[str, ...] = field(default_factory=tuple)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if not self.youtube_url:
            raise ValueError("youtube_url must not be empty")
        if self.current_attempt < 1:
            raise ValueError(f"current_attempt must be >= 1, got {self.current_attempt}")


@dataclass(frozen=True)
class ReflectionResult:
    """Output of the QA reflection loop for a stage."""

    best_critique: QACritique
    artifacts: tuple[Path, ...]
    attempts: int
    escalation_needed: bool = False

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError(f"attempts must be >= 1, got {self.attempts}")


@dataclass(frozen=True)
class MomentSelection:
    """Selected segment from a transcript with timestamps and rationale."""

    start_seconds: float
    end_seconds: float
    transcript_text: str
    rationale: str
    topic_match_score: float = 0.0

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError(f"start_seconds must be non-negative, got {self.start_seconds}")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"end_seconds ({self.end_seconds}) must be > start_seconds ({self.start_seconds})")
        duration = self.end_seconds - self.start_seconds
        if not 30.0 <= duration <= 120.0:
            raise ValueError(f"Segment duration must be 30-120s, got {duration:.1f}s")
        if not self.rationale:
            raise ValueError("rationale must not be empty")
        if not 0.0 <= self.topic_match_score <= 1.0:
            raise ValueError(f"topic_match_score must be 0.0-1.0, got {self.topic_match_score}")

    @property
    def duration_seconds(self) -> float:
        """Duration of the selected segment in seconds."""
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class LayoutClassification:
    """Classification of a single video frame's camera layout."""

    timestamp: float
    layout_name: str
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be non-negative, got {self.timestamp}")
        if not self.layout_name:
            raise ValueError("layout_name must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")


@dataclass(frozen=True)
class SegmentLayout:
    """A contiguous video segment with a classified layout and optional crop strategy."""

    start_seconds: float
    end_seconds: float
    layout_name: str
    crop_region: CropRegion | None = None

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError(f"start_seconds must be non-negative, got {self.start_seconds}")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"end_seconds ({self.end_seconds}) must be > start_seconds ({self.start_seconds})")
        if not self.layout_name:
            raise ValueError("layout_name must not be empty")


@dataclass(frozen=True)
class PipelineEvent:
    """Structured event emitted via EventBus for observability."""

    timestamp: str
    event_name: str
    stage: PipelineStage | None = None
    data: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.data, MappingProxyType):
            object.__setattr__(self, "data", _freeze_mapping(self.data))
        if not self.event_name:
            raise ValueError("event_name must not be empty")
