"""Domain event type constants — canonical event name strings for the pipeline EventBus."""

from __future__ import annotations

STAGE_ENTERED = "pipeline.stage_entered"
STAGE_COMPLETED = "pipeline.stage_completed"
RUN_FAILED = "pipeline.run_failed"
RUN_STARTED = "pipeline.run_started"
RUN_COMPLETED = "pipeline.run_completed"
