"""Domain event type constants for the pipeline event bus."""

from __future__ import annotations

# Stage lifecycle events
STAGE_ENTERED: str = "pipeline.stage_entered"
STAGE_COMPLETED: str = "pipeline.stage_completed"
STAGE_FAILED: str = "pipeline.stage_failed"

# Run lifecycle events
RUN_STARTED: str = "pipeline.run_started"
RUN_COMPLETED: str = "pipeline.run_completed"
RUN_FAILED: str = "pipeline.run_failed"
RUN_RESUMED: str = "pipeline.run_resumed"
