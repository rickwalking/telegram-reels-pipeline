"""Tests for PipelineEventEmitterService — event emission and projection updates."""

from __future__ import annotations

from types import MappingProxyType

from pipeline.application.services.pipeline_event_emitter_service import (
    ErrorEventPayload,
    PipelineEventEmitterService,
    QaEventPayload,
    StageEventPayload,
)
from pipeline.domain.event_types import (
    ERROR_OCCURRED,
    QA_GATE_FAILED,
    QA_GATE_PASSED,
    QA_GATE_REWORK,
    STAGE_COMPLETED,
    STAGE_ENTERED,
)
from pipeline.domain.events import RunStateProjection
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore

PIPELINE_RUN_ID = "test-run-001"


def _make_service() -> tuple[PipelineEventEmitterService, FakeEventStore, FakeStateStore]:
    """Create a service with fresh fakes."""
    event_store = FakeEventStore()
    state_store = FakeStateStore()
    service = PipelineEventEmitterService(event_store=event_store, state_store=state_store)
    return service, event_store, state_store


async def _seed_projection(state_store: FakeStateStore, stage: str = "router") -> None:
    """Seed a running projection in the fake state store."""
    projection = RunStateProjection(
        pipeline_run_id=PIPELINE_RUN_ID,
        current_stage=stage,
        execution_status="running",
    )
    await state_store.save_projection(projection)


class TestEmitStageEntered:
    """Tests for emit_stage_entered."""

    async def test_appends_stage_entered_event(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = StageEventPayload(pipeline_run_id=PIPELINE_RUN_ID, stage_name="router")

        # Act
        await service.emit_stage_entered(payload)

        # Assert
        assert len(event_store.events) == 1
        assert event_store.events[0].event_type == STAGE_ENTERED

    async def test_updates_projection_current_stage(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = StageEventPayload(pipeline_run_id=PIPELINE_RUN_ID, stage_name="research")

        # Act
        await service.emit_stage_entered(payload)

        # Assert
        projection = await state_store.load_projection(PIPELINE_RUN_ID)
        assert projection is not None
        assert projection.current_stage == "research"

    async def test_creates_projection_when_none_exists(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        payload = StageEventPayload(pipeline_run_id=PIPELINE_RUN_ID, stage_name="router")

        # Act
        await service.emit_stage_entered(payload)

        # Assert
        projection = await state_store.load_projection(PIPELINE_RUN_ID)
        assert projection is not None
        assert projection.current_stage == "router"


class TestEmitStageCompleted:
    """Tests for emit_stage_completed."""

    async def test_appends_stage_completed_event(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = StageEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            artifact_paths=("router-output.json",),
        )

        # Act
        await service.emit_stage_completed(payload)

        # Assert
        assert len(event_store.events) == 1
        assert event_store.events[0].event_type == STAGE_COMPLETED

    async def test_includes_artifact_paths_in_event_payload(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = StageEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            artifact_paths=("router-output.json", "research-output.json"),
        )

        # Act
        await service.emit_stage_completed(payload)

        # Assert
        event = event_store.events[0]
        assert event.payload["artifact_paths"] == ("router-output.json", "research-output.json")

    async def test_adds_stage_to_stages_completed(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = StageEventPayload(pipeline_run_id=PIPELINE_RUN_ID, stage_name="router")

        # Act
        await service.emit_stage_completed(payload)

        # Assert
        projection = await state_store.load_projection(PIPELINE_RUN_ID)
        assert projection is not None
        assert "router" in projection.stages_completed


class TestEmitQaGateResult:
    """Tests for emit_qa_gate_result — dict dispatch for QA decisions."""

    async def test_dispatches_pass_to_qa_gate_passed(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = QaEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            qa_decision="PASS",
        )

        # Act
        await service.emit_qa_gate_result(payload)

        # Assert
        assert event_store.events[0].event_type == QA_GATE_PASSED

    async def test_dispatches_rework_to_qa_gate_rework(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = QaEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            qa_decision="REWORK",
        )

        # Act
        await service.emit_qa_gate_result(payload)

        # Assert
        assert event_store.events[0].event_type == QA_GATE_REWORK

    async def test_dispatches_fail_to_qa_gate_failed(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = QaEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            qa_decision="FAIL",
        )

        # Act
        await service.emit_qa_gate_result(payload)

        # Assert
        assert event_store.events[0].event_type == QA_GATE_FAILED

    async def test_includes_critique_payload(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        critique = MappingProxyType({"score": 85, "gate": "router"})
        payload = QaEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            qa_decision="PASS",
            critique_payload=critique,
        )

        # Act
        await service.emit_qa_gate_result(payload)

        # Assert
        event = event_store.events[0]
        assert event.payload["score"] == 85

    async def test_raises_on_unknown_qa_decision(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = QaEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="router",
            qa_decision="UNKNOWN",
        )

        # Act & Assert
        try:
            await service.emit_qa_gate_result(payload)
            raise AssertionError("Should have raised ValueError")
        except ValueError as exc:
            assert "Unknown qa_decision" in str(exc)


class TestEmitErrorOccurred:
    """Tests for emit_error_occurred."""

    async def test_appends_error_occurred_event(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store)
        payload = ErrorEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="research",
            error_message="agent timeout",
        )

        # Act
        await service.emit_error_occurred(payload)

        # Assert
        assert len(event_store.events) == 1
        assert event_store.events[0].event_type == ERROR_OCCURRED

    async def test_marks_projection_as_failed(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store, stage="research")
        payload = ErrorEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="research",
            error_message="agent timeout",
        )

        # Act
        await service.emit_error_occurred(payload)

        # Assert
        projection = await state_store.load_projection(PIPELINE_RUN_ID)
        assert projection is not None
        assert projection.execution_status == "failed"

    async def test_stores_error_message_in_projection(self) -> None:
        # Arrange
        service, event_store, state_store = _make_service()
        await _seed_projection(state_store, stage="research")
        payload = ErrorEventPayload(
            pipeline_run_id=PIPELINE_RUN_ID,
            stage_name="research",
            error_message="agent timeout",
        )

        # Act
        await service.emit_error_occurred(payload)

        # Assert
        projection = await state_store.load_projection(PIPELINE_RUN_ID)
        assert projection is not None
        assert projection.error_message == "agent timeout"
