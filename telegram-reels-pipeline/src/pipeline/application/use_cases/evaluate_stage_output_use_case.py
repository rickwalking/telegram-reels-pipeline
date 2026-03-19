"""EvaluateStageOutputUseCase — record a QA evaluation result as a domain event."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import (
        PipelineEventEmitterService,
    )

from pipeline.application.services.pipeline_event_emitter_service import QaEventPayload


@dataclass(frozen=True)
class QaEvaluationCommand:
    """Command object encapsulating all inputs for a single QA evaluation.

    Uses a frozen dataclass to satisfy the max-3-args rule and provide
    deep immutability across the application layer boundary.
    """

    pipeline_run_id: str
    stage_name: str
    qa_decision: str  # "PASS", "REWORK", or "FAIL"
    critique_score: int

    def __post_init__(self) -> None:
        """Enforce basic semantic constraints at command construction time."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.stage_name:
            raise ValueError("stage_name must not be empty")
        if self.qa_decision not in {"PASS", "REWORK", "FAIL"}:
            raise ValueError(f"qa_decision must be PASS, REWORK, or FAIL; got '{self.qa_decision}'")
        if not 0 <= self.critique_score <= 100:
            raise ValueError(f"critique_score must be 0-100, got {self.critique_score}")


class EvaluateStageOutputUseCase:
    """Record a QA evaluation by emitting the appropriate domain event.

    Keeps the application layer free of infrastructure concerns — the
    PipelineEventEmitterService bridges to the EventBus without the use
    case knowing how or where events are persisted.
    """

    def __init__(self, emitter: PipelineEventEmitterService) -> None:
        self._emitter = emitter

    async def execute(self, command: QaEvaluationCommand) -> None:
        """Emit the QA gate result event for the given evaluation command."""
        payload = QaEventPayload(
            pipeline_run_id=command.pipeline_run_id,
            stage_name=command.stage_name,
            qa_decision=command.qa_decision,
            critique_score=command.critique_score,
        )
        await self._emitter.emit_qa_gate_result(payload)
