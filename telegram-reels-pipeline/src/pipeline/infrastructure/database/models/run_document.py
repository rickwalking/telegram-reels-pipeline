"""ODMantic Document models for the infrastructure layer."""

from typing import List, Optional
from odmantic import Model, Field
from datetime import datetime, timezone

class PipelineEventDocument(Model):
    """Immutable event stored in MongoDB, representing a state change in the pipeline."""
    run_id: str = Field(index=True)
    event_type: str = Field(index=True)  # e.g., 'stage_started', 'stage_completed', 'agent_error'
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stage: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    
    class Config:
        collection = "pipeline_events"

class RunStateDocument(Model):
    """Current state projection of a pipeline run, updated by projecting events."""
    run_id: str = Field(primary_field=True)
    youtube_url: str
    current_stage: str
    status: str
    stages_completed: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    last_event_id: Optional[str] = None # Used for SSE catch-up

    class Config:
        collection = "run_states"
