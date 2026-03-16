"""Unit tests for RunStateDocument mapper functions."""

from __future__ import annotations

from datetime import UTC, datetime

from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.mappers.run_state_mapper import (
    map_document_to_projection,
    map_projection_to_document,
)
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def _build_projection(
    *,
    pipeline_run_id: str = "run-001",
    youtube_url: str = "https://www.youtube.com/watch?v=TEST",
    trigger_source: str = "cli",
    current_stage: str = "router",
    execution_status: str = "pending",
    current_attempt_count: int = 0,
    qa_evaluation_status: str = "pending",
    completed_stages: tuple[str, ...] = (),
    escalation_status: str = "none",
    created_at: str = "2026-01-01T12:00:00+00:00",
    last_updated_at: str = "2026-01-01T12:00:00+00:00",
) -> RunStateProjection:
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url=youtube_url,
        trigger_source=trigger_source,
        current_stage=current_stage,
        execution_status=execution_status,
        current_attempt_count=current_attempt_count,
        qa_evaluation_status=qa_evaluation_status,
        completed_stages=completed_stages,
        escalation_status=escalation_status,
        created_at=created_at,
        last_updated_at=last_updated_at,
    )


def _build_document(
    *,
    pipeline_run_id: str = "run-001",
    youtube_url: str = "https://www.youtube.com/watch?v=TEST",
    trigger_source: str = "cli",
    current_stage: str = "router",
    execution_status: str = "pending",
    current_attempt_count: int = 0,
    qa_evaluation_status: str = "pending",
    completed_stages: list[str] | None = None,
    escalation_status: str = "none",
    created_at: datetime | None = None,
    last_updated_at: datetime | None = None,
) -> RunStateDocument:
    fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    return RunStateDocument(
        pipeline_run_id=pipeline_run_id,
        youtube_url=youtube_url,
        trigger_source=trigger_source,
        current_stage=current_stage,
        execution_status=execution_status,
        current_attempt_count=current_attempt_count,
        qa_evaluation_status=qa_evaluation_status,
        completed_stages=completed_stages or [],
        escalation_status=escalation_status,
        created_at=created_at or fixed,
        last_updated_at=last_updated_at or fixed,
    )


class TestMapProjectionToDocument:
    """Tests for map_projection_to_document."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        projection = _build_projection(
            pipeline_run_id="run-xyz",
            youtube_url="https://www.youtube.com/watch?v=ABC",
            trigger_source="telegram_bot",
            current_stage="research",
            execution_status="in_progress",
            current_attempt_count=2,
        )

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert document.pipeline_run_id == "run-xyz"
        assert document.youtube_url == "https://www.youtube.com/watch?v=ABC"
        assert document.trigger_source == "telegram_bot"
        assert document.current_stage == "research"
        assert document.execution_status == "in_progress"
        assert document.current_attempt_count == 2

    def test_converts_completed_stages_tuple_to_list(self) -> None:
        # Arrange
        projection = _build_projection(completed_stages=("router", "research", "transcript"))

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert isinstance(document.completed_stages, list)
        assert document.completed_stages == ["router", "research", "transcript"]

    def test_converts_iso_string_to_datetime(self) -> None:
        # Arrange
        projection = _build_projection(created_at="2026-03-10T08:00:00+00:00")

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert isinstance(document.created_at, datetime)


class TestMapDocumentToProjection:
    """Tests for map_document_to_projection."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        document = _build_document(
            pipeline_run_id="run-doc",
            youtube_url="https://www.youtube.com/watch?v=DOC",
            current_stage="transcript",
            current_attempt_count=3,
        )

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert projection.pipeline_run_id == "run-doc"
        assert projection.youtube_url == "https://www.youtube.com/watch?v=DOC"
        assert projection.current_stage == "transcript"
        assert projection.current_attempt_count == 3

    def test_converts_datetime_to_iso_string(self) -> None:
        # Arrange
        fixed = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
        document = _build_document(created_at=fixed)

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert isinstance(projection.created_at, str)
        assert "2026-03-15" in projection.created_at

    def test_converts_list_to_tuple(self) -> None:
        # Arrange
        document = _build_document(completed_stages=["router", "research"])

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert isinstance(projection.completed_stages, tuple)
        assert projection.completed_stages == ("router", "research")


class TestRunStateRoundTrip:
    """Round-trip: domain → document → domain."""

    def test_round_trip_preserves_all_fields(self) -> None:
        # Arrange
        original = _build_projection(
            pipeline_run_id="run-rt",
            trigger_source="telegram_bot",
            execution_status="in_progress",
            completed_stages=("router", "research"),
        )

        # Act
        document = map_projection_to_document(original)
        restored = map_document_to_projection(document)

        # Assert
        assert restored.pipeline_run_id == original.pipeline_run_id
        assert restored.trigger_source == original.trigger_source
        assert restored.execution_status == original.execution_status
        assert restored.completed_stages == original.completed_stages

    def test_round_trip_with_empty_completed_stages(self) -> None:
        # Arrange
        original = _build_projection(completed_stages=())

        # Act
        document = map_projection_to_document(original)
        restored = map_document_to_projection(document)

        # Assert
        assert restored.completed_stages == ()
