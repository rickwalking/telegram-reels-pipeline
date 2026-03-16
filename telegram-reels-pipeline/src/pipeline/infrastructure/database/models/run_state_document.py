"""ODMantic document model for run state projections."""

from __future__ import annotations

from datetime import UTC, datetime

from odmantic import Field, Model


class RunStateDocument(Model):
    """Current state projection of a pipeline run stored in MongoDB.

    This document is upserted on each state transition to maintain the latest
    known state of a run. It is the read-model side of the event-sourced design.
    """

    pipeline_run_id: str = Field(index=True, unique=True)
    youtube_url: str
    trigger_source: str = "cli"
    current_stage: str = "router"
    execution_status: str = "pending"
    current_attempt_count: int = 0
    qa_evaluation_status: str = "pending"
    completed_stages: list[str] = Field(default_factory=list)
    escalation_status: str = "none"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_event_id: str | None = None

    model_config = {"collection": "run_states"}  # type: ignore[assignment]
