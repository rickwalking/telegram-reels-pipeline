"""ResumePipelineRunUseCase — resume a paused pipeline run via API command."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pipeline.domain.errors import PipelineError
from pipeline.domain.event_types import RunStateProjection
from pipeline.domain.types import RunId

if TYPE_CHECKING:
    from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService
    from pipeline.domain.ports import StateStorePort

_RESUMABLE_STATUSES = frozenset({"paused"})


@dataclass(frozen=True)
class ResumeCommand:
    """Command to resume a paused pipeline run."""

    pipeline_run_id: str
    resume_from_stage: str = field(default="")
    operator_notes: str = field(default="")

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")


class PipelineRunNotFoundError(PipelineError):
    """Pipeline run not found in the state store."""


class PipelineRunNotResumableError(PipelineError):
    """Pipeline run is not in a resumable state (e.g., already running)."""


class ResumePipelineRunUseCase:
    """Resume a paused pipeline run.

    Validates the run exists and is in a resumable state, then emits
    a pipeline_resumed event and returns the updated projection.
    """

    def __init__(
        self,
        state_store: StateStorePort,
        event_emitter: PipelineEventEmitterService,
    ) -> None:
        self._state_store = state_store
        self._event_emitter = event_emitter

    async def execute(self, command: ResumeCommand) -> RunStateProjection:
        """Execute the resume command.

        Raises:
            PipelineRunNotFoundError: If the run does not exist.
            PipelineRunNotResumableError: If the run is not paused.
            ValidationError: If the command is invalid.
        """
        run_state = await self._state_store.load_state(RunId(command.pipeline_run_id))
        if run_state is None:
            raise PipelineRunNotFoundError(
                f"Pipeline run '{command.pipeline_run_id}' not found"
            )

        current_projection = await self._event_emitter.project_run_state(run_state)
        if current_projection.execution_status not in _RESUMABLE_STATUSES:
            raise PipelineRunNotResumableError(
                f"Pipeline run '{command.pipeline_run_id}' cannot be resumed: "
                f"current status is '{current_projection.execution_status}'"
            )

        _event, updated_projection = await self._event_emitter.emit_pipeline_resumed(
            run_state=run_state,
            operator_notes=command.operator_notes,
        )
        return updated_projection
