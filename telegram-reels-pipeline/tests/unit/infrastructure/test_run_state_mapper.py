"""Unit tests for RunStateDocument mapper functions.

Tests verify round-trip fidelity between domain projections and MongoDB documents.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pipeline.domain.enums import EscalationState, QAStatus, RunExecutionStatus, TriggerSource
from pipeline.domain.events import RunStateProjection
from pipeline.infrastructure.database.mappers.run_state_mapper import (
    map_document_to_projection,
    map_projection_to_document,
)
from pipeline.infrastructure.database.models.run_state_document import RunStateDocument


def _build_run_state_projection(
    *,
    pipeline_run_id: str = "run-001",
    youtube_url: str = "https://www.youtube.com/watch?v=TEST",
    trigger_source: TriggerSource = TriggerSource.CLI,
    current_stage: str = "router",
    execution_status: RunExecutionStatus = RunExecutionStatus.PENDING,
    current_attempt_count: int = 0,
    qa_evaluation_status: QAStatus = QAStatus.PENDING,
    completed_stages: tuple[str, ...] = (),
    escalation_status: EscalationState = EscalationState.NONE,
    created_at: datetime | None = None,
    last_updated_at: datetime | None = None,
    last_event_id: str | None = None,
) -> RunStateProjection:
    """Build a test RunStateProjection with sensible defaults."""
    fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
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
        created_at=created_at or fixed_timestamp,
        last_updated_at=last_updated_at or fixed_timestamp,
        last_event_id=last_event_id,
    )


def _build_run_state_document(
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
    last_event_id: str | None = None,
) -> RunStateDocument:
    """Build a test RunStateDocument with sensible defaults."""
    fixed_timestamp = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
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
        created_at=created_at or fixed_timestamp,
        last_updated_at=last_updated_at or fixed_timestamp,
        last_event_id=last_event_id,
    )


class TestMapProjectionToDocument:
    """Tests for map_projection_to_document."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 3, 10, 8, 0, 0, tzinfo=UTC)
        projection = _build_run_state_projection(
            pipeline_run_id="run-xyz",
            youtube_url="https://www.youtube.com/watch?v=ABC",
            trigger_source=TriggerSource.TELEGRAM,
            current_stage="research",
            execution_status=RunExecutionStatus.RUNNING,
            current_attempt_count=2,
            created_at=fixed_timestamp,
            last_updated_at=fixed_timestamp,
        )

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert document.pipeline_run_id == "run-xyz"
        assert document.youtube_url == "https://www.youtube.com/watch?v=ABC"
        assert document.trigger_source == "telegram"
        assert document.current_stage == "research"
        assert document.execution_status == "running"
        assert document.current_attempt_count == 2
        assert document.created_at == fixed_timestamp

    def test_serialises_enum_fields_to_string_values(self) -> None:
        # Arrange
        projection = _build_run_state_projection(
            trigger_source=TriggerSource.API,
            execution_status=RunExecutionStatus.FAILED,
            qa_evaluation_status=QAStatus.FAILED,
            escalation_status=EscalationState.QA_EXHAUSTED,
        )

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert document.trigger_source == "api"
        assert document.execution_status == "failed"
        assert document.qa_evaluation_status == "failed"
        assert document.escalation_status == "qa_exhausted"

    def test_serialises_completed_stages_tuple_to_list(self) -> None:
        # Arrange
        projection = _build_run_state_projection(
            completed_stages=("router", "research", "transcript"),
        )

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert isinstance(document.completed_stages, list)
        assert document.completed_stages == ["router", "research", "transcript"]

    def test_maps_optional_last_event_id_when_none(self) -> None:
        # Arrange
        projection = _build_run_state_projection(last_event_id=None)

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert document.last_event_id is None

    def test_maps_optional_last_event_id_when_set(self) -> None:
        # Arrange
        projection = _build_run_state_projection(last_event_id="evt-last")

        # Act
        document = map_projection_to_document(projection)

        # Assert
        assert document.last_event_id == "evt-last"


class TestMapDocumentToProjection:
    """Tests for map_document_to_projection."""

    def test_maps_all_scalar_fields_correctly(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 3, 10, 8, 0, 0, tzinfo=UTC)
        document = _build_run_state_document(
            pipeline_run_id="run-doc",
            youtube_url="https://www.youtube.com/watch?v=DOC",
            current_stage="transcript",
            current_attempt_count=3,
            created_at=fixed_timestamp,
        )

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert projection.pipeline_run_id == "run-doc"
        assert projection.youtube_url == "https://www.youtube.com/watch?v=DOC"
        assert projection.current_stage == "transcript"
        assert projection.current_attempt_count == 3
        assert projection.created_at == fixed_timestamp

    def test_deserialises_string_values_to_typed_enums(self) -> None:
        # Arrange
        document = _build_run_state_document(
            trigger_source="telegram",
            execution_status="completed",
            qa_evaluation_status="passed",
            escalation_status="error_escalated",
        )

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert projection.trigger_source == TriggerSource.TELEGRAM
        assert projection.execution_status == RunExecutionStatus.COMPLETED
        assert projection.qa_evaluation_status == QAStatus.PASSED
        assert projection.escalation_status == EscalationState.ERROR_ESCALATED

    def test_deserialises_completed_stages_list_to_tuple(self) -> None:
        # Arrange
        document = _build_run_state_document(
            completed_stages=["router", "research"],
        )

        # Act
        projection = map_document_to_projection(document)

        # Assert
        assert isinstance(projection.completed_stages, tuple)
        assert projection.completed_stages == ("router", "research")


class TestRunStateRoundTrip:
    """Round-trip tests: domain projection → document → domain projection."""

    def test_round_trip_preserves_all_fields(self) -> None:
        # Arrange
        fixed_timestamp = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)
        original_projection = _build_run_state_projection(
            pipeline_run_id="run-roundtrip",
            youtube_url="https://www.youtube.com/watch?v=ROUND",
            trigger_source=TriggerSource.TELEGRAM,
            current_stage="assembly",
            execution_status=RunExecutionStatus.RUNNING,
            current_attempt_count=1,
            qa_evaluation_status=QAStatus.PASSED,
            completed_stages=("router", "research", "transcript", "content", "layout_detective", "ffmpeg_engineer"),
            escalation_status=EscalationState.NONE,
            created_at=fixed_timestamp,
            last_updated_at=fixed_timestamp,
            last_event_id="evt-final",
        )

        # Act
        document = map_projection_to_document(original_projection)
        reconstructed_projection = map_document_to_projection(document)

        # Assert
        assert reconstructed_projection.pipeline_run_id == original_projection.pipeline_run_id
        assert reconstructed_projection.youtube_url == original_projection.youtube_url
        assert reconstructed_projection.trigger_source == original_projection.trigger_source
        assert reconstructed_projection.current_stage == original_projection.current_stage
        assert reconstructed_projection.execution_status == original_projection.execution_status
        assert reconstructed_projection.current_attempt_count == original_projection.current_attempt_count
        assert reconstructed_projection.qa_evaluation_status == original_projection.qa_evaluation_status
        assert reconstructed_projection.completed_stages == original_projection.completed_stages
        assert reconstructed_projection.escalation_status == original_projection.escalation_status
        assert reconstructed_projection.created_at == original_projection.created_at
        assert reconstructed_projection.last_updated_at == original_projection.last_updated_at
        assert reconstructed_projection.last_event_id == original_projection.last_event_id

    def test_round_trip_with_empty_completed_stages(self) -> None:
        # Arrange
        original_projection = _build_run_state_projection(completed_stages=())

        # Act
        document = map_projection_to_document(original_projection)
        reconstructed_projection = map_document_to_projection(document)

        # Assert
        assert reconstructed_projection.completed_stages == ()
        assert isinstance(reconstructed_projection.completed_stages, tuple)
