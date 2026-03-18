"""Exception handlers for FastAPI — maps domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from pipeline.domain.errors import PipelineError, ValidationError


def register_exception_handlers(application: FastAPI) -> None:
    """Register domain exception handlers on the FastAPI application."""

    @application.exception_handler(ValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.message},
        )

    @application.exception_handler(PipelineError)
    async def handle_pipeline_error(
        _request: Request,
        exc: PipelineError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message},
        )
