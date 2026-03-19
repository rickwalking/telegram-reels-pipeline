"""FastAPI exception handlers mapping domain errors to HTTP responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette import status

from pipeline.domain.errors import PipelineError
from pipeline.domain.errors import ValidationError as DomainValidationError
from pipeline.presentation.dtos.error_response_dto import ErrorResponseDTO

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI application instance."""
    application.add_exception_handler(DomainValidationError, _handle_domain_validation_error)
    application.add_exception_handler(PydanticValidationError, _handle_pydantic_validation_error)
    application.add_exception_handler(PipelineError, _handle_pipeline_error)


async def _handle_domain_validation_error(request: Request, exc: DomainValidationError) -> JSONResponse:
    """Map domain ValidationError to 400 Bad Request."""
    body = ErrorResponseDTO(
        error_code="DOMAIN_VALIDATION_ERROR",
        error_message=exc.message,
    )
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=body.model_dump())


async def _handle_pydantic_validation_error(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Map Pydantic ValidationError to 422 Unprocessable Entity."""
    error_details = [
        {"field": ".".join(str(loc) for loc in error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    body = ErrorResponseDTO(
        error_code="VALIDATION_ERROR",
        error_message="Request validation failed",
        details=error_details,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())


async def _handle_pipeline_error(request: Request, exc: PipelineError) -> JSONResponse:
    """Map generic PipelineError to 500 Internal Server Error."""
    logger.error("Pipeline error in %s %s: %s", request.method, request.url.path, exc.message)
    body = ErrorResponseDTO(
        error_code="PIPELINE_ERROR",
        error_message=exc.message,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump())
