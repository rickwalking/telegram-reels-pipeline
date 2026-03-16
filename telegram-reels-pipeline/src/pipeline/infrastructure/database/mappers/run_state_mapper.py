"""Pure mapping functions between RunStateProjection domain objects and RunStateDocument."""

from __future__ import annotations

from pipeline.domain.enums import EscalationState, QAStatus, RunExecutionStatus, TriggerSource
from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def map_projection_to_document(projection: RunStateProjection) -> RunStateDocument:
    """Convert a domain run-state projection to a MongoDB document for upsert.

    Enum values are serialised to their string representations for storage.
    """
    return RunStateDocument(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source.value,
        current_stage=projection.current_stage,
        execution_status=projection.execution_status.value,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status.value,
        completed_stages=list(projection.completed_stages),
        escalation_status=projection.escalation_status.value,
        created_at=projection.created_at,
        last_updated_at=projection.last_updated_at,
        last_event_id=projection.last_event_id,
    )


def map_document_to_projection(document: RunStateDocument) -> RunStateProjection:
    """Reconstruct a domain run-state projection from a persisted MongoDB document.

    String enum values are converted back to their typed enum counterparts.
    """
    return RunStateProjection(
        pipeline_run_id=document.pipeline_run_id,
        youtube_url=document.youtube_url,
        trigger_source=TriggerSource(document.trigger_source),
        current_stage=document.current_stage,
        execution_status=RunExecutionStatus(document.execution_status),
        current_attempt_count=document.current_attempt_count,
        qa_evaluation_status=QAStatus(document.qa_evaluation_status),
        completed_stages=tuple(document.completed_stages),
        escalation_status=EscalationState(document.escalation_status),
        created_at=document.created_at,
        last_updated_at=document.last_updated_at,
        last_event_id=document.last_event_id,
    )
