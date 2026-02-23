"""Domain models — frozen dataclasses for pipeline value objects and state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum, unique
from pathlib import Path
from types import MappingProxyType
from typing import Any

from pipeline.domain.enums import (
    EscalationState,
    NarrativeRole,
    PipelineStage,
    QADecision,
    QAStatus,
    RevisionType,
    ShotType,
)
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
    workspace_path: str = ""

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
class ContentPackage:
    """Generated content for Instagram posting alongside the Reel."""

    descriptions: tuple[str, ...]
    hashtags: tuple[str, ...]
    music_suggestion: str
    mood_category: str = ""

    def __post_init__(self) -> None:
        if not self.descriptions:
            raise ValueError("descriptions must not be empty")
        if not self.music_suggestion:
            raise ValueError("music_suggestion must not be empty")


@unique
class Veo3PromptVariant(StrEnum):
    """Allowed Veo 3 prompt variant types."""

    INTRO = "intro"
    BROLL = "broll"
    OUTRO = "outro"
    TRANSITION = "transition"


@dataclass(frozen=True)
class Veo3Prompt:
    """A single Veo 3 video generation prompt with its variant type."""

    variant: str
    prompt: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "variant", self.variant.strip())
        object.__setattr__(self, "prompt", self.prompt.strip())
        if self.variant not in {v.value for v in Veo3PromptVariant}:
            raise ValueError(f"variant must be one of {[v.value for v in Veo3PromptVariant]}, got '{self.variant}'")
        if not self.prompt:
            raise ValueError("prompt must not be empty")


@dataclass(frozen=True)
class LocalizedDescription:
    """A localized description for publishing."""

    language: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", self.language.strip())
        object.__setattr__(self, "text", self.text.strip())
        if not self.language:
            raise ValueError("language must not be empty")
        if not self.text:
            raise ValueError("text must not be empty")


@dataclass(frozen=True)
class PublishingAssets:
    """Publishing assets — localized descriptions, hashtags, and Veo 3 prompts."""

    descriptions: tuple[LocalizedDescription, ...]
    hashtags: tuple[str, ...]
    veo3_prompts: tuple[Veo3Prompt, ...]

    def __post_init__(self) -> None:
        if not self.descriptions:
            raise ValueError("descriptions must not be empty")
        if not self.hashtags:
            raise ValueError("hashtags must not be empty")
        for tag in self.hashtags:
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError("each hashtag must be a non-empty string")
            if not tag.strip().startswith("#"):
                raise ValueError(f"each hashtag must start with '#', got '{tag}'")
        object.__setattr__(self, "hashtags", tuple(t.strip() for t in self.hashtags))
        if not self.veo3_prompts:
            raise ValueError("veo3_prompts must not be empty")
        if len(self.veo3_prompts) > 4:
            raise ValueError(f"veo3_prompts must have 1-4 items, got {len(self.veo3_prompts)}")
        variants = [p.variant for p in self.veo3_prompts]
        if len(variants) != len(set(variants)):
            raise ValueError("veo3_prompts must have unique variants")
        if Veo3PromptVariant.BROLL.value not in variants:
            raise ValueError("veo3_prompts must include a 'broll' variant")


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


@dataclass(frozen=True)
class RevisionRequest:
    """User revision request classified by the Router Agent."""

    revision_type: RevisionType
    run_id: RunId
    user_message: str
    target_segment: int | None = None
    timestamp_hint: float | None = None
    extra_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if not self.user_message:
            raise ValueError("user_message must not be empty")
        if self.target_segment is not None and self.target_segment < 0:
            raise ValueError(f"target_segment must be non-negative, got {self.target_segment}")
        if self.extra_seconds < 0:
            raise ValueError(f"extra_seconds must be non-negative, got {self.extra_seconds}")


@dataclass(frozen=True)
class RevisionResult:
    """Output of a completed revision."""

    revision_type: RevisionType
    original_run_id: RunId
    artifacts: tuple[Path, ...] = field(default_factory=tuple)
    stages_rerun: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FaceGateConfig:
    """Configuration for hybrid face gate — spatial + confidence + temporal persistence."""

    # Area thresholds (percentage of frame area)
    min_area_pct: float = 0.8
    editorial_area_pct: float = 1.2
    hard_enter_area_pct: float = 1.6
    # Geometry thresholds
    min_separation_norm: float = 0.28
    min_cy_norm: float = 0.32
    min_size_ratio: float = 0.55
    min_confidence: float = 0.85
    # EMA temporal hysteresis
    ema_alpha: float = 0.4
    enter_threshold: float = 0.65
    exit_threshold: float = 0.45
    enter_persistence: int = 2
    exit_persistence: int = 3
    cooldown_seconds: float = 4.0
    # Component weights (must sum to 1.0)
    w_area: float = 0.40
    w_geometry: float = 0.20
    w_separation: float = 0.15
    w_vertical: float = 0.10
    w_size_ratio: float = 0.10
    w_confidence: float = 0.05

    def __post_init__(self) -> None:
        self._validate_ranges()
        total = (
            self.w_area + self.w_geometry + self.w_separation + self.w_vertical + self.w_size_ratio + self.w_confidence
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Component weights must sum to 1.0, got {total:.3f}")
        if self.enter_threshold <= self.exit_threshold:
            raise ValueError(
                f"enter_threshold ({self.enter_threshold}) must be > exit_threshold ({self.exit_threshold})"
            )
        if self.enter_persistence < 1:
            raise ValueError(f"enter_persistence must be >= 1, got {self.enter_persistence}")
        if self.exit_persistence < 1:
            raise ValueError(f"exit_persistence must be >= 1, got {self.exit_persistence}")
        if self.cooldown_seconds < 0:
            raise ValueError(f"cooldown_seconds must be non-negative, got {self.cooldown_seconds}")

    def _validate_ranges(self) -> None:
        if not 0.0 < self.ema_alpha <= 1.0:
            raise ValueError(f"ema_alpha must be in (0.0, 1.0], got {self.ema_alpha}")
        if not 0.0 <= self.enter_threshold <= 1.0:
            raise ValueError(f"enter_threshold must be in [0.0, 1.0], got {self.enter_threshold}")
        if not 0.0 <= self.exit_threshold <= 1.0:
            raise ValueError(f"exit_threshold must be in [0.0, 1.0], got {self.exit_threshold}")
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be in [0.0, 1.0], got {self.min_confidence}")
        if self.min_area_pct < 0:
            raise ValueError(f"min_area_pct must be non-negative, got {self.min_area_pct}")


@dataclass(frozen=True)
class FaceGateResult:
    """Per-frame result from the hybrid face gate evaluation."""

    raw_face_count: int
    editorial_face_count: int
    duo_score: float
    ema_score: float
    is_editorial_duo: bool
    shot_type: ShotType
    gate_reason: str

    def __post_init__(self) -> None:
        if self.raw_face_count < 0:
            raise ValueError(f"raw_face_count must be non-negative, got {self.raw_face_count}")
        if self.editorial_face_count < 0:
            raise ValueError(f"editorial_face_count must be non-negative, got {self.editorial_face_count}")
        if not 0.0 <= self.duo_score <= 1.0:
            raise ValueError(f"duo_score must be 0.0-1.0, got {self.duo_score}")
        if not 0.0 <= self.ema_score <= 1.0:
            raise ValueError(f"ema_score must be 0.0-1.0, got {self.ema_score}")
        if not self.gate_reason:
            raise ValueError("gate_reason must not be empty")


@dataclass(frozen=True)
class NarrativeMoment:
    """A transcript moment with a narrative role for extended shorts."""

    start_seconds: float
    end_seconds: float
    role: NarrativeRole
    transcript_excerpt: str

    def __post_init__(self) -> None:
        if self.start_seconds < 0:
            raise ValueError(f"start_seconds must be non-negative, got {self.start_seconds}")
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"end_seconds ({self.end_seconds}) must be > start_seconds ({self.start_seconds})")
        if not self.transcript_excerpt:
            raise ValueError("transcript_excerpt must not be empty")

    @property
    def duration_seconds(self) -> float:
        """Duration of this moment in seconds."""
        return self.end_seconds - self.start_seconds


NARRATIVE_ROLE_ORDER: tuple[NarrativeRole, ...] = (
    NarrativeRole.INTRO,
    NarrativeRole.BUILDUP,
    NarrativeRole.CORE,
    NarrativeRole.REACTION,
    NarrativeRole.CONCLUSION,
)


@dataclass(frozen=True)
class NarrativePlan:
    """Ordered collection of narrative moments composing an extended short."""

    moments: tuple[NarrativeMoment, ...]
    target_duration_seconds: float

    def __post_init__(self) -> None:
        if not self.moments:
            raise ValueError("moments must not be empty")
        if len(self.moments) > 5:
            raise ValueError(f"moments must have 1-5 items, got {len(self.moments)}")
        if self.target_duration_seconds <= 0:
            raise ValueError(f"target_duration_seconds must be positive, got {self.target_duration_seconds}")
        core_count = sum(1 for m in self.moments if m.role == NarrativeRole.CORE)
        if core_count != 1:
            raise ValueError(f"exactly one moment must have role CORE, got {core_count}")
        roles = [m.role for m in self.moments]
        if len(roles) != len(set(roles)):
            raise ValueError("each narrative role must appear at most once")

    @property
    def actual_duration_seconds(self) -> float:
        """Sum of all moment durations (excludes gaps between moments)."""
        return sum(m.duration_seconds for m in self.moments)

    @property
    def is_chronological(self) -> bool:
        """True if moments are ordered by source start_seconds."""
        return all(
            self.moments[i].start_seconds <= self.moments[i + 1].start_seconds for i in range(len(self.moments) - 1)
        )


@dataclass(frozen=True)
class ResourceSnapshot:
    """Point-in-time system resource measurements."""

    memory_used_bytes: int
    memory_total_bytes: int
    cpu_load_percent: float
    temperature_celsius: float | None = None

    def __post_init__(self) -> None:
        if self.memory_used_bytes < 0:
            raise ValueError(f"memory_used_bytes must be non-negative, got {self.memory_used_bytes}")
        if self.memory_total_bytes <= 0:
            raise ValueError(f"memory_total_bytes must be positive, got {self.memory_total_bytes}")
        if self.cpu_load_percent < 0.0:
            raise ValueError(f"cpu_load_percent must be non-negative, got {self.cpu_load_percent}")
        if self.temperature_celsius is not None and self.temperature_celsius < -273.15:
            raise ValueError(f"temperature_celsius below absolute zero, got {self.temperature_celsius}")
