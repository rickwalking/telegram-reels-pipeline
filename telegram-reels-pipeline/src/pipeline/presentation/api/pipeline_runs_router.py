"""FastAPI router for pipeline run endpoints (POST /api/runs, GET /api/runs/{id})."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase
from pipeline.domain.ports import EventStorePort, ProjectionStorePort
from pipeline.presentation.dtos.create_pipeline_run_request_dto import CreatePipelineRunRequestDTO
from pipeline.presentation.dtos.error_response_dto import ErrorResponseDTO
from pipeline.presentation.dtos.pipeline_run_response_dto import PipelineRunResponseDTO
from pipeline.presentation.mappers.run_state_mapper import (
    map_projection_to_response_dto,
    map_request_dto_to_command,
)

pipeline_runs_router = APIRouter(prefix="/api/runs", tags=["Pipeline Runs"])


async def get_event_store_port() -> EventStorePort:
    """Dependency stub — wired in story 23-2 via app override."""
    raise NotImplementedError("EventStorePort not wired yet — see story 23-2")


async def get_projection_store_port() -> ProjectionStorePort:
    """Dependency stub — wired in story 23-2 via app override."""
    raise NotImplementedError("ProjectionStorePort not wired yet — see story 23-2")


@pipeline_runs_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PipelineRunResponseDTO,
    responses={422: {"model": ErrorResponseDTO}},
    summary="Trigger a new pipeline run",
)
async def trigger_pipeline_run(
    request_dto: CreatePipelineRunRequestDTO,
    event_store: EventStorePort = Depends(get_event_store_port),  # noqa: B008
    projection_store: ProjectionStorePort = Depends(get_projection_store_port),  # noqa: B008
) -> PipelineRunResponseDTO:
    """Accept a YouTube URL and optional topic to start a new pipeline run."""
    command = map_request_dto_to_command(request_dto)
    use_case = TriggerPipelineRunUseCase(event_store, projection_store)
    projection = await use_case.execute(command)
    return map_projection_to_response_dto(projection)


@pipeline_runs_router.get(
    "/{pipeline_run_id}",
    response_model=PipelineRunResponseDTO,
    responses={404: {"model": ErrorResponseDTO}},
    summary="Retrieve pipeline run state",
)
async def get_pipeline_run(
    pipeline_run_id: str,
    projection_store: ProjectionStorePort = Depends(get_projection_store_port),  # noqa: B008
) -> PipelineRunResponseDTO:
    """Load and return the current state of a pipeline run by its ID."""
    projection = await projection_store.load_projection(pipeline_run_id)
    if projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline run '{pipeline_run_id}' not found",
        )
    return map_projection_to_response_dto(projection)
