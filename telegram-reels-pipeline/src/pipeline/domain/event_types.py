"""Domain event type constants for event-sourced pipeline state."""

from __future__ import annotations

PIPELINE_RUN_CREATED: str = "pipeline.run_created"
STAGE_ENTERED: str = "pipeline.stage_entered"
STAGE_COMPLETED: str = "pipeline.stage_completed"
QA_GATE_PASSED: str = "pipeline.qa_gate_passed"
QA_GATE_REWORK: str = "pipeline.qa_gate_rework"
QA_GATE_FAILED: str = "pipeline.qa_gate_failed"
ERROR_OCCURRED: str = "pipeline.error_occurred"
PIPELINE_PAUSED: str = "pipeline.pipeline_paused"
PIPELINE_RESUMED: str = "pipeline.pipeline_resumed"
