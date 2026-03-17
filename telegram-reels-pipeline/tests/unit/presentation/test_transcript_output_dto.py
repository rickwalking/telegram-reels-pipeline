"""Unit tests for TranscriptOutputDTO — valid moments and temporal ordering validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.presentation.dtos.transcript_output_dto import MomentSelectionItemDTO, TranscriptOutputDTO


def _make_valid_moment_payload(
    start_seconds: float = 10.0,
    end_seconds: float = 70.0,
) -> dict[str, object]:
    """Return a minimal valid payload for MomentSelectionItemDTO."""
    return {
        "moment_start_seconds": start_seconds,
        "moment_end_seconds": end_seconds,
        "selected_quote": "AI is transforming everything",
        "narrative_role": "core",
        "selection_reasoning": "High engagement moment with clear argument",
    }


def _make_valid_transcript_payload(moments: list[dict[str, object]] | None = None) -> dict[str, object]:
    """Return a minimal valid payload for TranscriptOutputDTO."""
    if moments is None:
        moments = [_make_valid_moment_payload()]
    return {
        "pipeline_run_id": "run-2026-abc123",
        "stage_name": "transcript",
        "generated_at": "2026-03-16T10:00:00Z",
        "moments": moments,
    }


class TestMomentSelectionItemDTOValidMoments:
    def test_valid_moment_is_accepted(self) -> None:
        # Arrange
        payload = _make_valid_moment_payload()

        # Act
        dto = MomentSelectionItemDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.moment_start_seconds == 10.0
        assert dto.moment_end_seconds == 70.0
        assert dto.selected_quote == "AI is transforming everything"
        assert dto.narrative_role == "core"

    def test_moment_at_zero_start_is_valid(self) -> None:
        # Arrange
        payload = _make_valid_moment_payload(start_seconds=0.0, end_seconds=60.0)

        # Act
        dto = MomentSelectionItemDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.moment_start_seconds == 0.0

    def test_fractional_seconds_are_valid(self) -> None:
        # Arrange
        payload = _make_valid_moment_payload(start_seconds=10.5, end_seconds=70.75)

        # Act
        dto = MomentSelectionItemDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.moment_start_seconds == 10.5
        assert dto.moment_end_seconds == 70.75


class TestMomentSelectionItemDTOTemporalOrdering:
    def test_end_before_start_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_moment_payload(start_seconds=70.0, end_seconds=10.0)

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            MomentSelectionItemDTO(**payload)  # type: ignore[arg-type]
        assert "moment_end_seconds must be greater than moment_start_seconds" in str(excinfo.value)

    def test_end_equal_to_start_raises_validation_error(self) -> None:
        # Arrange
        payload = _make_valid_moment_payload(start_seconds=30.0, end_seconds=30.0)

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            MomentSelectionItemDTO(**payload)  # type: ignore[arg-type]
        assert "moment_end_seconds must be greater than moment_start_seconds" in str(excinfo.value)


class TestTranscriptOutputDTOValidMomentsList:
    def test_single_moment_is_accepted(self) -> None:
        # Arrange
        payload = _make_valid_transcript_payload()

        # Act
        dto = TranscriptOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert len(dto.moments) == 1

    def test_multiple_moments_are_accepted(self) -> None:
        # Arrange
        moments = [
            _make_valid_moment_payload(start_seconds=10.0, end_seconds=70.0),
            _make_valid_moment_payload(start_seconds=100.0, end_seconds=160.0),
            _make_valid_moment_payload(start_seconds=200.0, end_seconds=260.0),
        ]
        payload = _make_valid_transcript_payload(moments=moments)

        # Act
        dto = TranscriptOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert len(dto.moments) == 3

    def test_empty_moments_list_is_accepted_by_dto(self) -> None:
        # Arrange — business rule (non-empty) is enforced by domain, not DTO
        payload = _make_valid_transcript_payload(moments=[])

        # Act
        dto = TranscriptOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.moments == []

    def test_extra_field_on_transcript_dto_is_rejected(self) -> None:
        # Arrange
        payload = _make_valid_transcript_payload()
        payload["extra_key"] = "rejected"

        # Act & Assert
        with pytest.raises(ValidationError):
            TranscriptOutputDTO(**payload)  # type: ignore[arg-type]
