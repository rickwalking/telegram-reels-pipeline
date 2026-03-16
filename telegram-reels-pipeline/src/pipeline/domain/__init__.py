"""Domain layer public API — re-exports for all domain models, enums, and events."""

from __future__ import annotations

from pipeline.domain.enums import (
    EscalationState,
    FramingStyle,
    FramingStyleState,
    NarrativeRole,
    PipelineStage,
    QADecision,
    QAStatus,
    RevisionType,
    RunExecutionStatus,
    ShotType,
    TransitionKind,
    TriggerSource,
)
from pipeline.domain.event_types import (
    ERROR_OCCURRED,
    ESCALATION_AGENT_ERROR,
    ESCALATION_LAYOUT_UNKNOWN,
    ESCALATION_MANUAL_PAUSE,
    ESCALATION_QA_EXHAUSTED,
    PIPELINE_PAUSED,
    PIPELINE_RESUMED,
    PIPELINE_RUN_CLAIMED,
    PIPELINE_RUN_COMPLETED,
    PIPELINE_RUN_CREATED,
    PIPELINE_RUN_FAILED,
    QA_BEST_OF_THREE_SELECTED,
    QA_GATE_FAILED,
    QA_GATE_PASSED,
    QA_GATE_REWORK,
    STAGE_COMPLETED,
    STAGE_ENTERED,
    STAGE_OUTPUT_SAVED,
    WORKSPACE_CLEANED,
)
from pipeline.domain.events import (
    CreatePipelineRunCommand,
    PipelineStateEvent,
    RunStateProjection,
)

__all__ = [
    # Enums
    "EscalationState",
    "FramingStyle",
    "FramingStyleState",
    "NarrativeRole",
    "PipelineStage",
    "QADecision",
    "QAStatus",
    "RevisionType",
    "RunExecutionStatus",
    "ShotType",
    "TransitionKind",
    "TriggerSource",
    # Event models
    "CreatePipelineRunCommand",
    "PipelineStateEvent",
    "RunStateProjection",
    # Event type constants
    "ERROR_OCCURRED",
    "ESCALATION_AGENT_ERROR",
    "ESCALATION_LAYOUT_UNKNOWN",
    "ESCALATION_MANUAL_PAUSE",
    "ESCALATION_QA_EXHAUSTED",
    "PIPELINE_PAUSED",
    "PIPELINE_RESUMED",
    "PIPELINE_RUN_CLAIMED",
    "PIPELINE_RUN_COMPLETED",
    "PIPELINE_RUN_CREATED",
    "PIPELINE_RUN_FAILED",
    "QA_BEST_OF_THREE_SELECTED",
    "QA_GATE_FAILED",
    "QA_GATE_PASSED",
    "QA_GATE_REWORK",
    "STAGE_COMPLETED",
    "STAGE_ENTERED",
    "STAGE_OUTPUT_SAVED",
    "WORKSPACE_CLEANED",
]
