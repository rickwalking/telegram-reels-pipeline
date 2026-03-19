"""FastAPI application factory — creates and configures the ASGI application."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine

from pipeline.application.services.pipeline_orchestrator_worker import (
    OrchestratorWorkerConfig,
    PipelineOrchestratorWorker,
)
from pipeline.infrastructure.database.adapters.mongodb_event_store_adapter import MongoDbEventStoreAdapter
from pipeline.infrastructure.database.adapters.mongodb_state_store_adapter import MongoDbStateStoreAdapter
from pipeline.presentation.api.exception_handlers import register_exception_handlers
from pipeline.presentation.api.pipeline_runs_router import (
    get_event_store_port,
    get_state_store_port,
    pipeline_runs_router,
)

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS: tuple[str, ...] = ("http://localhost:5173", "http://192.168.1.142:5173")
MONGODB_URI = "mongodb://localhost:27017"
MONGODB_DATABASE = "telegram_reels_pipeline"


@asynccontextmanager
async def application_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Connect MongoDB, wire adapters, start orchestrator worker."""
    motor_client = AsyncIOMotorClient(MONGODB_URI)
    odmantic_engine = AIOEngine(client=motor_client, database=MONGODB_DATABASE)

    event_store = MongoDbEventStoreAdapter(odmantic_engine)
    state_store = MongoDbStateStoreAdapter(odmantic_engine)

    application.dependency_overrides[get_event_store_port] = lambda: event_store
    application.dependency_overrides[get_state_store_port] = lambda: state_store

    worker = PipelineOrchestratorWorker(config=OrchestratorWorkerConfig())
    application.state.orchestrator_worker = worker
    worker_task = asyncio.create_task(worker.start_processing_loop())
    logger.info("Backend started — MongoDB connected, orchestrator worker running")

    yield

    worker.request_graceful_shutdown()
    await worker_task
    motor_client.close()
    logger.info("Backend stopped — MongoDB disconnected")


def create_fastapi_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    application = FastAPI(
        title="Telegram Reels Pipeline API",
        description="Omni-Channel REST API for triggering and monitoring pipeline runs.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=application_lifespan,
    )
    _add_cors_middleware(application)
    register_exception_handlers(application)
    application.include_router(pipeline_runs_router)
    return application


def _add_cors_middleware(application: FastAPI) -> None:
    """Attach CORS middleware allowing the Vite dev server origin."""
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
