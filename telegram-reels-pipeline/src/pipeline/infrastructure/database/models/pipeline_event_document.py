"""ODMantic document model for immutable pipeline events."""

from __future__ import annotations

from datetime import UTC, datetime

from odmantic import Field, Model


class PipelineEventDocument(Model):
    """Immutable event stored in MongoDB.

    One document per state-change event. Never updated after insertion.
    """

    event_id: str = Field(index=True, unique=True)
    pipeline_run_id: str = Field(index=True)
    event_type: str = Field(index=True)
    stage_name: str = ""
    payload_data: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = {"collection": "pipeline_events"}  # type: ignore[assignment]
