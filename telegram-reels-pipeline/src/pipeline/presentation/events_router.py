"""FastAPI router for pipeline event DVR endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from pipeline.domain.pipeline_event_store_port import PipelineEventStorePort
from pipeline.domain.types import EventId, RunId
from pipeline.presentation.event_dtos import (
    PipelineEventDetailDTO,
    PipelineEventListResponseDTO,
)
from pipeline.presentation.event_mapper import (
    map_stored_event_to_detail_dto,
    map_stored_event_to_item_dto,
)

MAXIMUM_PAGE_SIZE = 200


def create_events_router(
    event_store: PipelineEventStorePort,
) -> APIRouter:
    """Build the events APIRouter with the injected event store."""
    router = APIRouter(prefix="/api/runs", tags=["events"])

    @router.get(
        "/{pipeline_run_id}/events",
        response_model=PipelineEventListResponseDTO,
        summary="List events for a pipeline run",
        description="Returns paginated events ordered by created_at ascending.",
    )
    async def list_pipeline_run_events(
        pipeline_run_id: str,
        offset: int = Query(default=0, ge=0, description="Pagination offset"),
        limit: int = Query(default=50, ge=1, le=MAXIMUM_PAGE_SIZE, description="Page size"),
    ) -> PipelineEventListResponseDTO:
        """Return paginated events for a pipeline run."""
        events, total_count = await event_store.list_events_for_run(
            pipeline_run_id=RunId(pipeline_run_id),
            offset=offset,
            limit=limit,
        )
        items = [map_stored_event_to_item_dto(event) for event in events]
        return PipelineEventListResponseDTO(
            items=items,
            total=total_count,
            offset=offset,
            limit=limit,
        )

    @router.get(
        "/{pipeline_run_id}/events/{event_id}",
        response_model=PipelineEventDetailDTO,
        summary="Get a single pipeline event",
        description="Returns full event payload. 404 if not found.",
        responses={404: {"description": "Event not found"}},
    )
    async def get_pipeline_run_event_detail(
        pipeline_run_id: str,
        event_id: str,
    ) -> PipelineEventDetailDTO:
        """Return full detail for a single event."""
        stored_event = await event_store.get_event_by_id(
            pipeline_run_id=RunId(pipeline_run_id),
            event_id=EventId(event_id),
        )
        if stored_event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return map_stored_event_to_detail_dto(stored_event)

    return router
