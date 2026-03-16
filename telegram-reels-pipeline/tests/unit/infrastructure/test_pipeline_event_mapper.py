"""Unit tests for PipelineEventDocument mapper functions.

Tests verify round-trip fidelity between domain events and MongoDB documents.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import MappingProxyType

import pytest

from pipeline.domain.events import PipelineStateEvent
from pipeline.infrastructure.database.mappers.pipeline_event_mapper import (
    map_document_to_domain_event,
    map_domain_event_to_document,
)
from pipeline.infrastructure.database.models.pipeline_event_document import PipelineEventDocument


def _build_pipeline_state_event(
    *,
    event_id: str = "evt-001",
    pipeline_run_id: str = "run-abc",
    event_type: str = "stage_started",
    stage_name: str = "router",
    payload: MappingProxyType[str, object] | None = None,
    occurred_at: datetime | None = None,
) -> PipelineStateEvent:
    """Build a test PipelineStateEvent with sensible defaults."""
    return PipelineStateEvent(
        event_id=event_id,
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        stage_name=stage_name,
        payload=payload or MappingProxyType({}),
        occurred_at=occurred_at or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


def _build_pipeline_event_document(
    *,
    event_id: str = "evt-001",
    pipeline_run_id: str = "run-abc",
    event_type: str = "stage_started",
    stage_name: str = "router",
    payload_data: dict[str, object] | None = None,
    created_at: datetime | None = None,
) -> PipelineEventDocument:
    """Build a test PipelineEventDocument with sensible defaults."""
    return PipelineEventDocument(
        event_id=event_id,
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        stage_name=stage_name,
        payload_data=payload_data or {},
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


class TestMapDomainEventToDocument:
    """Tests for map_domain_event_to_document."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
        domain_event = _build_pipeline_state_event(
            event_id="evt-xyz",
            pipeline_run_id="run-123",
            event_type="stage_completed",
            stage_name="research",
            occurred_at=fixed_timestamp,
        )

        # Act
        document = map_domain_event_to_document(domain_event)

        # Assert
        assert document.event_id == "evt-xyz"
        assert document.pipeline_run_id == "run-123"
        assert document.event_type == "stage_completed"
        assert document.stage_name == "research"
        assert document.created_at == fixed_timestamp

    def test_serialises_mapping_proxy_payload_to_plain_dict(self) -> None:
        # Arrange
        payload = MappingProxyType({"attempt": 2, "duration_seconds": 45.5})
        domain_event = _build_pipeline_state_event(payload=payload)

        # Act
        document = map_domain_event_to_document(domain_event)

        # Assert
        assert isinstance(document.payload_data, dict)
        assert document.payload_data == {"attempt": 2, "duration_seconds": 45.5}

    def test_maps_empty_payload_to_empty_dict(self) -> None:
        # Arrange
        domain_event = _build_pipeline_state_event(payload=MappingProxyType({}))

        # Act
        document = map_domain_event_to_document(domain_event)

        # Assert
        assert document.payload_data == {}


class TestMapDocumentToDomainEvent:
    """Tests for map_document_to_domain_event."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
        document = _build_pipeline_event_document(
            event_id="evt-abc",
            pipeline_run_id="run-456",
            event_type="stage_failed",
            stage_name="ffmpeg_engineer",
            created_at=fixed_timestamp,
        )

        # Act
        domain_event = map_document_to_domain_event(document)

        # Assert
        assert domain_event.event_id == "evt-abc"
        assert domain_event.pipeline_run_id == "run-456"
        assert domain_event.event_type == "stage_failed"
        assert domain_event.stage_name == "ffmpeg_engineer"
        assert domain_event.occurred_at == fixed_timestamp

    def test_deserialises_dict_payload_to_mapping_proxy(self) -> None:
        # Arrange
        document = _build_pipeline_event_document(payload_data={"score": 85, "gate": "qa"})

        # Act
        domain_event = map_document_to_domain_event(document)

        # Assert
        assert isinstance(domain_event.payload, MappingProxyType)
        assert domain_event.payload["score"] == 85
        assert domain_event.payload["gate"] == "qa"

    def test_payload_mapping_proxy_is_immutable(self) -> None:
        # Arrange
        document = _build_pipeline_event_document(payload_data={"key": "value"})

        # Act
        domain_event = map_document_to_domain_event(document)

        # Assert
        with pytest.raises(TypeError):
            domain_event.payload["key"] = "mutated"  # type: ignore[index]


class TestPipelineEventRoundTrip:
    """Round-trip tests: domain event → document → domain event."""

    def test_round_trip_preserves_all_fields(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 3, 1, 9, 0, 0, tzinfo=UTC)
        original_event = _build_pipeline_state_event(
            event_id="evt-roundtrip",
            pipeline_run_id="run-roundtrip",
            event_type="qa_passed",
            stage_name="transcript",
            payload=MappingProxyType({"score": 92, "attempts": 1}),
            occurred_at=fixed_timestamp,
        )

        # Act
        document = map_domain_event_to_document(original_event)
        reconstructed_event = map_document_to_domain_event(document)

        # Assert
        assert reconstructed_event.event_id == original_event.event_id
        assert reconstructed_event.pipeline_run_id == original_event.pipeline_run_id
        assert reconstructed_event.event_type == original_event.event_type
        assert reconstructed_event.stage_name == original_event.stage_name
        assert reconstructed_event.occurred_at == original_event.occurred_at
        assert dict(reconstructed_event.payload) == dict(original_event.payload)

    def test_round_trip_with_empty_payload(self) -> None:
        # Arrange
        original_event = _build_pipeline_state_event(payload=MappingProxyType({}))

        # Act
        document = map_domain_event_to_document(original_event)
        reconstructed_event = map_document_to_domain_event(document)

        # Assert
        assert dict(reconstructed_event.payload) == {}
        assert isinstance(reconstructed_event.payload, MappingProxyType)
