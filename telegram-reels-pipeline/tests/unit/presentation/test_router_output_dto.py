"""Unit tests for RouterOutputDTO — valid payloads, extra fields, and missing fields."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO


def _make_valid_router_payload() -> dict[str, object]:
    """Return a minimal valid payload for RouterOutputDTO construction."""
    return {
        "pipeline_run_id": "run-2026-abc123",
        "stage_name": "router",
        "generated_at": "2026-03-16T10:00:00Z",
        "tier": "short",
        "topic_focus": "AI safety",
        "elicitation_answers": {"tone": "casual", "length": "60s"},
        "style_preference": "auto",
    }


class TestRouterOutputDTOValidPayload:
    def test_valid_payload_is_accepted(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()

        # Act
        dto = RouterOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.pipeline_run_id == "run-2026-abc123"
        assert dto.stage_name == "router"
        assert dto.tier == "short"
        assert dto.topic_focus == "AI safety"
        assert dto.elicitation_answers == {"tone": "casual", "length": "60s"}
        assert dto.style_preference == "auto"

    def test_default_style_preference_is_auto(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        del payload["style_preference"]

        # Act
        dto = RouterOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.style_preference == "auto"

    def test_empty_elicitation_answers_is_valid(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        payload["elicitation_answers"] = {}

        # Act
        dto = RouterOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.elicitation_answers == {}


class TestRouterOutputDTOExtraFieldsRejected:
    def test_extra_field_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        payload["unknown_field"] = "unexpected"

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            RouterOutputDTO(**payload)  # type: ignore[arg-type]
        assert "extra_forbidden" in str(excinfo.value) or "Extra inputs" in str(excinfo.value)

    def test_multiple_extra_fields_raise_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        payload["foo"] = "bar"
        payload["baz"] = 42

        # Act & Assert
        with pytest.raises(ValidationError):
            RouterOutputDTO(**payload)  # type: ignore[arg-type]


class TestRouterOutputDTOMissingRequiredFields:
    def test_missing_pipeline_run_id_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        del payload["pipeline_run_id"]

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            RouterOutputDTO(**payload)  # type: ignore[arg-type]
        assert "pipeline_run_id" in str(excinfo.value)

    def test_missing_tier_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        del payload["tier"]

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            RouterOutputDTO(**payload)  # type: ignore[arg-type]
        assert "tier" in str(excinfo.value)

    def test_missing_topic_focus_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        del payload["topic_focus"]

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            RouterOutputDTO(**payload)  # type: ignore[arg-type]
        assert "topic_focus" in str(excinfo.value)

    def test_missing_elicitation_answers_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_router_payload()
        del payload["elicitation_answers"]

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            RouterOutputDTO(**payload)  # type: ignore[arg-type]
        assert "elicitation_answers" in str(excinfo.value)
