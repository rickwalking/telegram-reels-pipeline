"""Pure mapping functions between RunStateProjection domain objects and RunStateDocument."""

from __future__ import annotations

from datetime import datetime, timezone

from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def map_projection_to_document(projection: RunStateProjection) -> RunStateDocument:
    """Convert a domain run-state projection to a MongoDB document for upsert.

    Domain uses str fields; document uses str fields + datetime for timestamps.
    """
    return RunStateDocument(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=projection.execution_status,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=list(projection.completed_stages),
        escalation_status=projection.escalation_status,
        created_at=datetime.fromisoformat(projection.created_at) if isinstance(projection.created_at, str) else projection.created_at,
        last_updated_at=datetime.fromisoformat(projection.last_updated_at) if isinstance(projection.last_updated_at, str) else projection.last_updated_at,
    )


def map_document_to_projection(document: RunStateDocument) -> RunStateProjection:
    """Reconstruct a domain run-state projection from a persisted MongoDB document.

    Document datetime fields are converted to ISO strings for the domain model.
    """
    return RunStateProjection(
        pipeline_run_id=document.pipeline_run_id,
        youtube_url=document.youtube_url,
        trigger_source=document.trigger_source,
        current_stage=document.current_stage,
        execution_status=document.execution_status,
        current_attempt_count=document.current_attempt_count,
        qa_evaluation_status=document.qa_evaluation_status,
        completed_stages=tuple(document.completed_stages),
        escalation_status=document.escalation_status,
        created_at=document.created_at.isoformat() if hasattr(document.created_at, 'isoformat') else str(document.created_at),
        last_updated_at=document.last_updated_at.isoformat() if hasattr(document.last_updated_at, 'isoformat') else str(document.last_updated_at),
    )
