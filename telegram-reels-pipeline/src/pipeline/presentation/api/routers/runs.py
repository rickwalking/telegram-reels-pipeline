"""FastAPI router for triggering and monitoring pipeline runs."""

from fastapi import APIRouter, Depends, HTTPException, status
from pipeline.presentation.dtos.run_dtos import CreateRunRequestDTO, RunStateResponseDTO
from pipeline.application.mappers.run_mappers import map_runstate_to_response_dto
from pipeline.domain.ports import StateStorePort
# In a real app, this would be injected via a dependency framework
from pipeline.infrastructure.database.repositories.mongo_state_store import MongoStateStore

router = APIRouter(prefix="/runs", tags=["runs"])

# Mock dependency injection for demonstration
async def get_state_store() -> StateStorePort:
    return MongoStateStore("mongodb://localhost:27017")

@router.post("/", response_model=RunStateResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: CreateRunRequestDTO,
    state_store: StateStorePort = Depends(get_state_store)
):
    """Trigger a new pipeline run."""
    # Logic to initialize the run and save to the database would go here
    # For now, we mock the creation
    from pipeline.domain.models import RunState, PipelineStage
    from pipeline.domain.types import RunId
    import uuid
    from datetime import datetime, timezone

    new_run = RunState(
        run_id=RunId(str(uuid.uuid4())),
        youtube_url=str(request.youtube_url),
        current_stage=PipelineStage.ROUTER, # Assuming starting stage
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat()
    )
    
    await state_store.save_state(new_run)
    return map_runstate_to_response_dto(new_run)

@router.get("/{run_id}", response_model=RunStateResponseDTO)
async def get_run_status(
    run_id: str,
    state_store: StateStorePort = Depends(get_state_store)
):
    """Get the current status of a pipeline run."""
    run_state = await state_store.load_state(run_id)
    if not run_state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        
    return map_runstate_to_response_dto(run_state)
