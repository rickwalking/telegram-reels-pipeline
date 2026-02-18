"""FSM transition table and guard definitions — pure data, no I/O."""

from types import MappingProxyType

from pipeline.domain.enums import FramingStyleState, PipelineStage

# Transition table: (current_stage, event) -> next_stage
# Events: qa_pass, qa_rework, qa_fail, stage_complete, escalation_requested, escalation_resolved
TRANSITIONS: MappingProxyType[tuple[PipelineStage, str], PipelineStage] = MappingProxyType(
    {
        # Normal forward progression (QA pass -> next stage)
        (PipelineStage.ROUTER, "qa_pass"): PipelineStage.RESEARCH,
        (PipelineStage.RESEARCH, "qa_pass"): PipelineStage.TRANSCRIPT,
        (PipelineStage.TRANSCRIPT, "qa_pass"): PipelineStage.CONTENT,
        (PipelineStage.CONTENT, "qa_pass"): PipelineStage.LAYOUT_DETECTIVE,
        (PipelineStage.LAYOUT_DETECTIVE, "qa_pass"): PipelineStage.FFMPEG_ENGINEER,
        (PipelineStage.FFMPEG_ENGINEER, "qa_pass"): PipelineStage.ASSEMBLY,
        (PipelineStage.ASSEMBLY, "qa_pass"): PipelineStage.DELIVERY,
        (PipelineStage.DELIVERY, "stage_complete"): PipelineStage.COMPLETED,
        # QA rework — stay on same stage for retry
        (PipelineStage.ROUTER, "qa_rework"): PipelineStage.ROUTER,
        (PipelineStage.RESEARCH, "qa_rework"): PipelineStage.RESEARCH,
        (PipelineStage.TRANSCRIPT, "qa_rework"): PipelineStage.TRANSCRIPT,
        (PipelineStage.CONTENT, "qa_rework"): PipelineStage.CONTENT,
        (PipelineStage.LAYOUT_DETECTIVE, "qa_rework"): PipelineStage.LAYOUT_DETECTIVE,
        (PipelineStage.FFMPEG_ENGINEER, "qa_rework"): PipelineStage.FFMPEG_ENGINEER,
        (PipelineStage.ASSEMBLY, "qa_rework"): PipelineStage.ASSEMBLY,
        # QA fail — remain on stage (recovery chain handles escalation)
        (PipelineStage.ROUTER, "qa_fail"): PipelineStage.ROUTER,
        (PipelineStage.RESEARCH, "qa_fail"): PipelineStage.RESEARCH,
        (PipelineStage.TRANSCRIPT, "qa_fail"): PipelineStage.TRANSCRIPT,
        (PipelineStage.CONTENT, "qa_fail"): PipelineStage.CONTENT,
        (PipelineStage.LAYOUT_DETECTIVE, "qa_fail"): PipelineStage.LAYOUT_DETECTIVE,
        (PipelineStage.FFMPEG_ENGINEER, "qa_fail"): PipelineStage.FFMPEG_ENGINEER,
        (PipelineStage.ASSEMBLY, "qa_fail"): PipelineStage.ASSEMBLY,
        # Escalation — stay on stage, wait for user
        (PipelineStage.LAYOUT_DETECTIVE, "escalation_requested"): PipelineStage.LAYOUT_DETECTIVE,
        (PipelineStage.LAYOUT_DETECTIVE, "escalation_resolved"): PipelineStage.LAYOUT_DETECTIVE,
        # Unrecoverable failure — pipeline cannot continue
        (PipelineStage.ROUTER, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.RESEARCH, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.TRANSCRIPT, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.CONTENT, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.LAYOUT_DETECTIVE, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.FFMPEG_ENGINEER, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.ASSEMBLY, "unrecoverable_error"): PipelineStage.FAILED,
        (PipelineStage.DELIVERY, "unrecoverable_error"): PipelineStage.FAILED,
    }
)

# Framing style FSM — transitions driven by face-count changes and user requests.
# Events: face_count_increase, face_count_decrease, pip_requested, split_requested,
#         screen_share_detected, screen_share_ended
FRAMING_TRANSITIONS: MappingProxyType[tuple[FramingStyleState, str], FramingStyleState] = MappingProxyType(
    {
        # Solo ↔ Duo transitions
        (FramingStyleState.SOLO, "face_count_increase"): FramingStyleState.DUO_SPLIT,
        (FramingStyleState.DUO_SPLIT, "face_count_decrease"): FramingStyleState.SOLO,
        (FramingStyleState.DUO_PIP, "face_count_decrease"): FramingStyleState.SOLO,
        # Duo mode switching
        (FramingStyleState.DUO_SPLIT, "pip_requested"): FramingStyleState.DUO_PIP,
        (FramingStyleState.DUO_PIP, "split_requested"): FramingStyleState.DUO_SPLIT,
        # Screen share transitions
        (FramingStyleState.SOLO, "screen_share_detected"): FramingStyleState.SCREEN_SHARE,
        (FramingStyleState.DUO_SPLIT, "screen_share_detected"): FramingStyleState.SCREEN_SHARE,
        (FramingStyleState.DUO_PIP, "screen_share_detected"): FramingStyleState.SCREEN_SHARE,
        (FramingStyleState.SCREEN_SHARE, "face_count_increase"): FramingStyleState.DUO_SPLIT,
        (FramingStyleState.SCREEN_SHARE, "screen_share_ended"): FramingStyleState.SOLO,
        # Cinematic solo (single speaker, high-quality close-up)
        (FramingStyleState.SOLO, "cinematic_requested"): FramingStyleState.CINEMATIC_SOLO,
        (FramingStyleState.CINEMATIC_SOLO, "face_count_increase"): FramingStyleState.DUO_SPLIT,
        (FramingStyleState.CINEMATIC_SOLO, "screen_share_detected"): FramingStyleState.SCREEN_SHARE,
    }
)

# Valid framing events
FRAMING_EVENTS: frozenset[str] = frozenset(
    {
        "face_count_increase",
        "face_count_decrease",
        "pip_requested",
        "split_requested",
        "screen_share_detected",
        "screen_share_ended",
        "cinematic_requested",
    }
)


def get_framing_state(current: FramingStyleState, event: str) -> FramingStyleState | None:
    """Look up the next framing state for a given (current, event) pair. Returns None if invalid."""
    return FRAMING_TRANSITIONS.get((current, event))


def is_valid_framing_transition(current: FramingStyleState, event: str) -> bool:
    """Check whether a framing transition is defined in the table."""
    return (current, event) in FRAMING_TRANSITIONS


# Ordered tuple of processing stages (excludes terminal states)
STAGE_ORDER: tuple[PipelineStage, ...] = (
    PipelineStage.ROUTER,
    PipelineStage.RESEARCH,
    PipelineStage.TRANSCRIPT,
    PipelineStage.CONTENT,
    PipelineStage.LAYOUT_DETECTIVE,
    PipelineStage.FFMPEG_ENGINEER,
    PipelineStage.ASSEMBLY,
    PipelineStage.DELIVERY,
)

# Terminal states — no transitions out
TERMINAL_STAGES: frozenset[PipelineStage] = frozenset({PipelineStage.COMPLETED, PipelineStage.FAILED})

# Maximum QA attempts before best-of-three selection
MAX_QA_ATTEMPTS: int = 3


def is_valid_transition(current: PipelineStage, event: str) -> bool:
    """Check whether a transition is defined in the table."""
    return (current, event) in TRANSITIONS


def get_next_stage(current: PipelineStage, event: str) -> PipelineStage | None:
    """Look up the next stage for a given (current, event) pair. Returns None if invalid."""
    return TRANSITIONS.get((current, event))


def is_terminal(stage: PipelineStage) -> bool:
    """Check whether a stage is a terminal state."""
    return stage in TERMINAL_STAGES
