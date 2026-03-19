"""Mapper: RunStateProjection domain object → RunStateDocument."""

from __future__ import annotations

from datetime import datetime

from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def map_projection_to_document(projection: RunStateProjection) -> RunStateDocument:
    """Convert a domain run-state projection to a MongoDB document for upsert."""
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
