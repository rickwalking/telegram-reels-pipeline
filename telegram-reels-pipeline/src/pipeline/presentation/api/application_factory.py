"""FastAPI application factory — creates and configures the ASGI application."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pipeline.presentation.api.exception_handlers import register_exception_handlers
from pipeline.presentation.api.pipeline_runs_router import pipeline_runs_router

ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]


def create_fastapi_application() -> FastAPI:
    """Factory function to create and configure the FastAPI application."""
    application = FastAPI(
        title="Telegram Reels Pipeline API",
        description="Omni-Channel REST API for triggering and monitoring pipeline runs.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
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
