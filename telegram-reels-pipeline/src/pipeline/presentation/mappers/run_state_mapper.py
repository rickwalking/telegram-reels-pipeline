"""RunStateMapper — maps domain RunState to presentation-layer response DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.domain.models import RunState


def map_run_state_to_response_dict(run_state: RunState) -> dict[str, object]:
    """Convert a domain RunState to a serializable response dictionary.

    This mapper lives in the presentation layer because it references
    the presentation contract (response shape). Domain and application
    layers must not depend on this.
    """
    return {
        "run_id": run_state.run_id,
        "youtube_url": run_state.youtube_url,
        "current_stage": run_state.current_stage.value,
        "current_attempt": run_state.current_attempt,
        "qa_status": run_state.qa_status.value,
        "stages_completed": list(run_state.stages_completed),
        "escalation_state": run_state.escalation_state.value,
        "created_at": run_state.created_at,
        "updated_at": run_state.updated_at,
        "workspace_path": run_state.workspace_path,
    }
