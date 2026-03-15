"""Mappers to translate between Domain entities and DTOs."""

from pipeline.domain.models import RunState
from pipeline.presentation.dtos.run_dtos import RunStateResponseDTO

def map_runstate_to_response_dto(run_state: RunState) -> RunStateResponseDTO:
    """Map a Domain RunState to a DTO for API presentation."""
    # Determine user-friendly status
    status = "Running"
    if run_state.escalation_state != "none": # Assuming string representation or enum
        status = "Needs Human Review"
    elif "assembly" in run_state.stages_completed: # Assuming assembly is the final stage
        status = "Completed"

    return RunStateResponseDTO(
        run_id=run_state.run_id,
        youtube_url=run_state.youtube_url,
        current_stage=run_state.current_stage,
        status=status,
        stages_completed=list(run_state.stages_completed),
        created_at=run_state.created_at,
        updated_at=run_state.updated_at
    )
