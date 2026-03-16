"""Domain event type constants for the event-sourced pipeline state store."""

from __future__ import annotations

PIPELINE_RUN_CREATED: str = "pipeline_run_created"
PIPELINE_STAGE_ENTERED: str = "pipeline_stage_entered"
PIPELINE_STAGE_COMPLETED: str = "pipeline_stage_completed"
PIPELINE_RUN_COMPLETED: str = "pipeline_run_completed"
PIPELINE_RUN_FAILED: str = "pipeline_run_failed"
PIPELINE_ESCALATED: str = "pipeline_escalated"
