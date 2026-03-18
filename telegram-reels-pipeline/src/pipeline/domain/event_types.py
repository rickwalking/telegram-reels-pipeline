"""Constants for pipeline event types — ubiquitous language for state transitions."""
from __future__ import annotations

# Pipeline lifecycle events
PIPELINE_RUN_CREATED = "pipeline.run_created"
PIPELINE_RUN_CLAIMED = "pipeline.run_claimed"
PIPELINE_RUN_COMPLETED = "pipeline.run_completed"
PIPELINE_RUN_FAILED = "pipeline.run_failed"
PIPELINE_PAUSED = "pipeline.paused"
PIPELINE_RESUMED = "pipeline.resumed"

# Stage lifecycle events
STAGE_ENTERED = "pipeline.stage_entered"
STAGE_COMPLETED = "pipeline.stage_completed"

# QA gate events
QA_GATE_PASSED = "qa.gate_passed"
QA_GATE_REWORK = "qa.gate_rework"
QA_GATE_FAILED = "qa.gate_failed"
QA_BEST_OF_THREE_SELECTED = "qa.best_of_three_selected"

# Error events
ERROR_OCCURRED = "pipeline.error_occurred"

# Escalation events
ESCALATION_LAYOUT_UNKNOWN = "escalation.layout_unknown"
ESCALATION_QA_EXHAUSTED = "escalation.qa_exhausted"
ESCALATION_AGENT_ERROR = "escalation.agent_error"
ESCALATION_MANUAL_PAUSE = "escalation.manual_pause"

# Workspace events
WORKSPACE_CLEANED = "workspace.cleaned"

# Stage output events
STAGE_OUTPUT_SAVED = "stage.output_saved"

# Legacy aliases
RUN_FAILED = PIPELINE_RUN_FAILED
RUN_STARTED = PIPELINE_RUN_CREATED
RUN_COMPLETED = PIPELINE_RUN_COMPLETED
