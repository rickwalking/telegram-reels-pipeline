"""EscalatePipelineRunUseCase — transition a run to the escalated/paused state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import (
        PipelineEventEmitterService,
    )


@dataclass(frozen=True)
class EscalationCommand:
    """Command to escalate a pipeline run and pause it for operator intervention.

    Attributes:
        pipeline_run_id: Unique identifier of the run to escalate.
        escalation_reason: Canonical reason key — one of ``layout_unknown``,
            ``qa_exhausted``, or ``agent_error``.
        stage_name: Human-readable name of the stage that triggered escalation.
    """

    pipeline_run_id: str
    escalation_reason: str
    stage_name: str

    def __post_init__(self) -> None:
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.escalation_reason:
            raise ValueError("escalation_reason must not be empty")
        if not self.stage_name:
            raise ValueError("stage_name must not be empty")


def _build_escalation_dispatch(
    emitter: PipelineEventEmitterService,
    stage_name: str,
) -> dict[str, Callable[[], None]]:
    """Build the reason → emit callable dispatch table."""
    return {
        "layout_unknown": lambda: emitter.emit_escalation_layout_unknown(stage_name),
        "qa_exhausted": lambda: emitter.emit_escalation_qa_exhausted(stage_name),
        "agent_error": lambda: emitter.emit_escalation_agent_error(stage_name),
    }


class EscalatePipelineRunUseCase:
    """Escalate a pipeline run to the paused state and notify observability layer.

    Emits the domain-specific escalation event (keyed on ``escalation_reason``)
    followed by a ``pipeline_paused`` event.  The projection on the emitter is
    updated synchronously so downstream SSE consumers see the new state.
    """

    def __init__(self, event_emitter: PipelineEventEmitterService) -> None:
        self._event_emitter = event_emitter

    async def execute(self, command: EscalationCommand) -> None:
        """Execute the escalation command.

        Raises:
            ValueError: When ``command.escalation_reason`` is not a recognised key.
        """
        dispatch = _build_escalation_dispatch(
            self._event_emitter, command.stage_name
        )
        escalation_emitter = dispatch.get(command.escalation_reason)
        if escalation_emitter is None:
            raise ValueError(
                f"Unknown escalation_reason: '{command.escalation_reason}'. "
                f"Valid values: {sorted(dispatch)}"
            )
        escalation_emitter()
        self._event_emitter.emit_pipeline_paused(command.escalation_reason)
