"""Tests for event mapper — domain to DTO conversion."""

from __future__ import annotations

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent, StoredPipelineEvent
from pipeline.domain.types import EventId, RunId
from pipeline.presentation.event_mapper import (
    map_stored_event_to_detail_dto,
    map_stored_event_to_item_dto,
)


def _make_stored_event(
    event_name: str = "pipeline.stage_entered",
    stage: PipelineStage | None = PipelineStage.ROUTER,
) -> StoredPipelineEvent:
    """Build a StoredPipelineEvent for testing."""
    return StoredPipelineEvent(
        event_id=EventId("evt-abc123"),
        pipeline_run_id=RunId("run-001"),
        event=PipelineEvent(
            timestamp="2026-03-18T10:00:00Z",
            event_name=event_name,
            stage=stage,
            data={"attempt": 1},
        ),
    )


class TestMapStoredEventToItemDTO:
    """Tests for map_stored_event_to_item_dto."""

    def test_maps_all_fields(self) -> None:
        # Arrange
        stored = _make_stored_event()

        # Act
        dto = map_stored_event_to_item_dto(stored)

        # Assert
        assert dto.event_id == "evt-abc123"
        assert dto.pipeline_run_id == "run-001"
        assert dto.timestamp == "2026-03-18T10:00:00Z"
        assert dto.event_name == "pipeline.stage_entered"
        assert dto.stage == "router"
        assert dto.data == {"attempt": 1}

    def test_maps_none_stage(self) -> None:
        # Arrange
        stored = _make_stored_event(stage=None)

        # Act
        dto = map_stored_event_to_item_dto(stored)

        # Assert
        assert dto.stage is None


class TestMapStoredEventToDetailDTO:
    """Tests for map_stored_event_to_detail_dto."""

    def test_maps_all_fields(self) -> None:
        # Arrange
        stored = _make_stored_event()

        # Act
        dto = map_stored_event_to_detail_dto(stored)

        # Assert
        assert dto.event_id == "evt-abc123"
        assert dto.pipeline_run_id == "run-001"
        assert dto.event_name == "pipeline.stage_entered"
        assert dto.data == {"attempt": 1}
