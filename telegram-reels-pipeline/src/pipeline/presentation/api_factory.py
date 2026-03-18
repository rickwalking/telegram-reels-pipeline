"""FastAPI application factory — wires routers and exception handlers."""

from __future__ import annotations

from fastapi import FastAPI

from pipeline.domain.pipeline_event_store_port import PipelineEventStorePort
from pipeline.presentation.events_router import create_events_router
from pipeline.presentation.exception_handlers import register_exception_handlers


def create_api_application(
    event_store: PipelineEventStorePort,
) -> FastAPI:
    """Build and return a fully-configured FastAPI application."""
    application = FastAPI(
        title="Pipeline DVR API",
        description="Historical event scrubber for pipeline runs",
        version="0.1.0",
    )
    register_exception_handlers(application)
    events_router = create_events_router(event_store=event_store)
    application.include_router(events_router)
    return application
