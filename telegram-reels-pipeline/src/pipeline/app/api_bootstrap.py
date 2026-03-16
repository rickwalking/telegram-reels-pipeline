"""API composition root — creates the FastAPI app with dependency overrides."""

from __future__ import annotations

from fastapi import FastAPI

from pipeline.presentation.api.application_factory import create_fastapi_application


def create_api_application() -> FastAPI:
    """Build the FastAPI app configured for production use.

    Dependency overrides for EventStorePort and ProjectionStorePort
    will be wired in story 23-2 when MongoDB adapters are implemented.
    """
    return create_fastapi_application()
