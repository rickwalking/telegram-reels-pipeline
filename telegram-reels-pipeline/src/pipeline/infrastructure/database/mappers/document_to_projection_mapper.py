"""Mapper: RunStateDocument → RunStateProjection domain object."""

from __future__ import annotations

from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def map_document_to_projection(document: RunStateDocument) -> RunStateProjection:
    """Reconstruct a domain run-state projection from a persisted MongoDB document."""
    created_at_iso = document.created_at.isoformat() if hasattr(document.created_at, "isoformat") else str(document.created_at)
    last_updated_iso = document.last_updated_at.isoformat() if hasattr(document.last_updated_at, "isoformat") else str(document.last_updated_at)
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
        created_at=created_at_iso,
        last_updated_at=last_updated_iso,
    )
