"""Presentation DTO for structured API error responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorResponseDTO(BaseModel):
    """Uniform error envelope returned by all API error handlers."""

    model_config = ConfigDict(strict=True, extra="forbid")

    error_code: str
    error_message: str
    details: list[dict[str, str]] | None = None
