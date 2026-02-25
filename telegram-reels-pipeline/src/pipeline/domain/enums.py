"""Domain enums — pipeline stage progression, QA decisions, and state flags."""

from enum import Enum, unique


@unique
class PipelineStage(Enum):
    """Ordered pipeline stages matching BMAD workflow step files."""

    ROUTER = "router"
    RESEARCH = "research"
    TRANSCRIPT = "transcript"
    CONTENT = "content"
    LAYOUT_DETECTIVE = "layout_detective"
    FFMPEG_ENGINEER = "ffmpeg_engineer"
    VEO3_AWAIT = "veo3_await"
    ASSEMBLY = "assembly"
    DELIVERY = "delivery"
    COMPLETED = "completed"
    FAILED = "failed"


@unique
class QADecision(Enum):
    """QA gate verdict for a stage artifact."""

    PASS = "PASS"
    REWORK = "REWORK"
    FAIL = "FAIL"


@unique
class EscalationState(Enum):
    """Pipeline-level escalation flags."""

    NONE = "none"
    LAYOUT_UNKNOWN = "layout_unknown"
    QA_EXHAUSTED = "qa_exhausted"
    ERROR_ESCALATED = "error_escalated"


@unique
class QAStatus(Enum):
    """QA evaluation status for the current pipeline stage."""

    PENDING = "pending"
    PASSED = "passed"
    REWORK = "rework"
    FAILED = "failed"


@unique
class FramingStyle(Enum):
    """User-selectable framing style for reel video layout."""

    DEFAULT = "default"
    SPLIT_HORIZONTAL = "split_horizontal"
    PIP = "pip"
    AUTO = "auto"


@unique
class FramingStyleState(Enum):
    """Runtime framing state for dynamic style switching FSM."""

    SOLO = "solo"
    DUO_SPLIT = "duo_split"
    DUO_PIP = "duo_pip"
    SCREEN_SHARE = "screen_share"
    CINEMATIC_SOLO = "cinematic_solo"


@unique
class ShotType(Enum):
    """Classified shot type based on face spatial analysis."""

    CLOSE_UP = "close_up"
    MEDIUM_SHOT = "medium_shot"
    TWO_SHOT = "two_shot"
    WIDE_SHOT = "wide_shot"
    SCREEN_SHARE = "screen_share"


@unique
class NarrativeRole(Enum):
    """Narrative arc role for a transcript moment in extended shorts."""

    INTRO = "intro"
    BUILDUP = "buildup"
    CORE = "core"
    REACTION = "reaction"
    CONCLUSION = "conclusion"


@unique
class TransitionKind(Enum):
    """Transition type between segments — controls xfade style and duration."""

    STYLE_CHANGE = "style_change"
    NARRATIVE_BOUNDARY = "narrative_boundary"


@unique
class RevisionType(Enum):
    """User-requested revision categories routed by Router Agent."""

    EXTEND_MOMENT = "extend_moment"
    FIX_FRAMING = "fix_framing"
    DIFFERENT_MOMENT = "different_moment"
    ADD_CONTEXT = "add_context"
