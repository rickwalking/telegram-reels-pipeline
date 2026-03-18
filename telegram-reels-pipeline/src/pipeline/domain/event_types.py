"""Domain event type constants — names for all pipeline state events."""

from __future__ import annotations

# Stage lifecycle events
STAGE_ENTERED: str = "pipeline.stage_entered"
STAGE_COMPLETED: str = "pipeline.stage_completed"
STAGE_FAILED: str = "pipeline.stage_failed"

# Run lifecycle events
RUN_STARTED: str = "pipeline.run_started"
RUN_COMPLETED: str = "pipeline.run_completed"
RUN_FAILED: str = "pipeline.run_failed"

# Download-specific events
DOWNLOAD_STARTED: str = "pipeline.download_started"
DOWNLOAD_COMPLETED: str = "pipeline.download_completed"
DOWNLOAD_FAILED: str = "pipeline.download_failed"
