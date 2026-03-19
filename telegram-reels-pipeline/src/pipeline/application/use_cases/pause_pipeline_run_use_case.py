"""PausePipelineRunUseCase — pauses an in-progress pipeline run by emitting a paused event."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService
    from pipeline.domain.ports import StateStorePort

from pipeline.application.use_cases.run_state_projection import (
    EXECUTION_STATUS_IN_PROGRESS,
    RunStateProjection,
)
from pipeline.domain.errors import ValidationError
from pipeline.domain.types import RunId

_RUN_NOT_FOUND_MESSAGE = "Pipeline run '{pipeline_run_id}' not found."
_NOT_PAUSABLE_MESSAGE = (
    "Pipeline run '{pipeline_run_id}' cannot be paused: execution_status is '{execution_status}'."
)


@dataclass(frozen=True)
class PauseCommand:
    """Command object carrying the intent to pause a pipeline run.

    Attributes:
        pipeline_run_id: The unique identifier of the run to pause.
        reason: Optional human-readable explanation for the pause.
    """

    pipeline_run_id: str
    reason: str = ""


class PausePipelineRunUseCase:
    """Application use case: pause an in-progress pipeline run.

    Validates that the run exists and is pausable, then emits a paused event
    via the PipelineEventEmitterService. Returns the updated projection.
    """

    def __init__(
        self,
        state_store: StateStorePort,
        event_emitter: PipelineEventEmitterService,
    ) -> None:
        self._state_store = state_store
        self._event_emitter = event_emitter

    async def execute(self, command: PauseCommand) -> RunStateProjection:
        """Execute the pause command.

        Steps:
        1. Load the run projection — raise ValidationError if not found.
        2. Validate the run is pausable (execution_status == in_progress).
        3. Emit pipeline_paused event.
        4. Return the current projection (state is event-sourced externally).

        Raises:
            ValidationError: If run not found or not in a pausable state.
        """
        run_id = RunId(command.pipeline_run_id)
        run_state = await self._state_store.load_state(run_id)

        if run_state is None:
            raise ValidationError(
                _RUN_NOT_FOUND_MESSAGE.format(pipeline_run_id=command.pipeline_run_id)
            )

        projection = RunStateProjection.from_run_state(run_state)

        if projection.execution_status != EXECUTION_STATUS_IN_PROGRESS:
            raise ValidationError(
                _NOT_PAUSABLE_MESSAGE.format(
                    pipeline_run_id=command.pipeline_run_id,
                    execution_status=projection.execution_status,
                )
            )

        await self._event_emitter.emit_pipeline_paused(
            pipeline_run_id=command.pipeline_run_id,
            reason=command.reason,
        )

        return projection
