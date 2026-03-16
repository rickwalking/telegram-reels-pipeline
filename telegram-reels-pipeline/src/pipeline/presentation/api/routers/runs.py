"""Runs router — REST API endpoints for triggering and querying pipeline runs."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from pipeline.domain.ports.state_store_port import StateStorePort

router = APIRouter(prefix="/api/runs", tags=["runs"])


def get_state_store_port() -> StateStorePort:
    """Dependency provider for StateStorePort — wired in composition root (Story 22-3)."""
    raise NotImplementedError("StateStorePort wiring not yet configured — see Story 22-3")


StateStorePortDep = Annotated[StateStorePort, Depends(get_state_store_port)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a new pipeline run",
    description="Start processing a YouTube URL through the full pipeline.",
    responses={
        status.HTTP_201_CREATED: {"description": "Pipeline run created successfully"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid request payload"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "State store not available"},
    },
)
async def trigger_pipeline_run(
    state_store: StateStorePortDep,
) -> dict[str, str]:
    """Trigger a new pipeline run for a given YouTube URL.

    Returns a 201 response with the new run ID.
    Wiring of the request body and full logic is completed in Story 22-3.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Pipeline run triggering not yet implemented — see Story 22-3",
    )
