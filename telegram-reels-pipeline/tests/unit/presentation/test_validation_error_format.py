"""Unit tests for AgentValidationErrorDTO — construction and field validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.presentation.dtos.agent_validation_error_dto import AgentValidationErrorDTO, FieldErrorDetailDTO


def _make_valid_field_error_payload() -> dict[str, object]:
    """Return a minimal valid payload for FieldErrorDetailDTO."""
    return {
        "field_name": "moment_end_seconds",
        "error_message": "moment_end_seconds must be greater than moment_start_seconds",
        "received_value": "10.0",
    }


def _make_valid_validation_error_payload(
    invalid_fields: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Return a minimal valid payload for AgentValidationErrorDTO."""
    if invalid_fields is None:
        invalid_fields = [_make_valid_field_error_payload()]
    return {
        "error_type": "validation_error",
        "invalid_fields": invalid_fields,
    }


class TestFieldErrorDetailDTOConstruction:
    def test_valid_field_error_is_accepted(self) -> None:
        # Arrange
        payload = _make_valid_field_error_payload()

        # Act
        dto = FieldErrorDetailDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.field_name == "moment_end_seconds"
        assert dto.error_message == "moment_end_seconds must be greater than moment_start_seconds"
        assert dto.received_value == "10.0"

    def test_missing_field_name_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_field_error_payload()
        del payload["field_name"]

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            FieldErrorDetailDTO(**payload)  # type: ignore[arg-type]
        assert "field_name" in str(excinfo.value)

    def test_extra_field_on_field_error_dto_is_rejected(self) -> None:
        # Arrange
        payload = _make_valid_field_error_payload()
        payload["unexpected"] = "value"

        # Act & Assert
        with pytest.raises(ValidationError):
            FieldErrorDetailDTO(**payload)  # type: ignore[arg-type]


class TestAgentValidationErrorDTOConstruction:
    def test_valid_validation_error_is_accepted(self) -> None:
        # Arrange
        payload = _make_valid_validation_error_payload()

        # Act
        dto = AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.error_type == "validation_error"
        assert len(dto.invalid_fields) == 1
        assert dto.suggested_correction is None

    def test_default_error_type_is_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_validation_error_payload()
        del payload["error_type"]

        # Act
        dto = AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.error_type == "validation_error"

    def test_suggested_correction_is_optional(self) -> None:
        # Arrange
        payload = _make_valid_validation_error_payload()
        payload["suggested_correction"] = "Ensure moment_end_seconds > moment_start_seconds"

        # Act
        dto = AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.suggested_correction == "Ensure moment_end_seconds > moment_start_seconds"

    def test_multiple_invalid_fields_are_accepted(self) -> None:
        # Arrange
        invalid_fields: list[dict[str, object]] = [
            _make_valid_field_error_payload(),
            {
                "field_name": "tier",
                "error_message": "field required",
                "received_value": "None",
            },
        ]
        payload = _make_valid_validation_error_payload(invalid_fields=invalid_fields)

        # Act
        dto = AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert len(dto.invalid_fields) == 2
        assert dto.invalid_fields[0].field_name == "moment_end_seconds"
        assert dto.invalid_fields[1].field_name == "tier"

    def test_empty_invalid_fields_list_is_accepted_by_dto(self) -> None:
        # Arrange — empty list is syntactically valid; business rule is separate
        payload = _make_valid_validation_error_payload(invalid_fields=[])

        # Act
        dto = AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.invalid_fields == []

    def test_extra_field_on_validation_error_dto_is_rejected(self) -> None:
        # Arrange
        payload = _make_valid_validation_error_payload()
        payload["extra_key"] = "forbidden"

        # Act & Assert
        with pytest.raises(ValidationError):
            AgentValidationErrorDTO(**payload)  # type: ignore[arg-type]
