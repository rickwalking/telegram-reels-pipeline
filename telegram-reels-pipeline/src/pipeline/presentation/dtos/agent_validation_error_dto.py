"""DTO for agent input validation error responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FieldErrorDetailDTO(BaseModel):
    """Detail for a single field validation failure including the received value."""

    model_config = ConfigDict(strict=True, extra="forbid")

    field_name: str
    error_message: str
    received_value: str


class AgentValidationErrorDTO(BaseModel):
    """Structured validation error response returned to agents when DTO validation fails."""

    model_config = ConfigDict(strict=True, extra="forbid")

    error_type: str = "validation_error"
    invalid_fields: list[FieldErrorDetailDTO]
    suggested_correction: str | None = None
