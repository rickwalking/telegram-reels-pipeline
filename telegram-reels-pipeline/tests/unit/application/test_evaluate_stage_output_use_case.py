"""Unit tests for EvaluateStageOutputUseCase."""

from __future__ import annotations

import pytest

from pipeline.application.event_bus import EventBus
from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService
from pipeline.application.use_cases.evaluate_stage_output_use_case import (
    EvaluateStageOutputUseCase,
    QaEvaluationCommand,
)
from pipeline.domain.event_types import QA_GATE_FAILED, QA_GATE_PASSED, QA_GATE_REWORK
from tests.fakes.fake_event_store import FakeEventStore


@pytest.fixture
def fake_event_store() -> FakeEventStore:
    return FakeEventStore()


@pytest.fixture
def event_bus(fake_event_store: FakeEventStore) -> EventBus:
    bus = EventBus()
    bus.subscribe(fake_event_store)
    return bus


@pytest.fixture
def emitter_service(event_bus: EventBus) -> PipelineEventEmitterService:
    return PipelineEventEmitterService(event_bus=event_bus)


@pytest.fixture
def use_case(emitter_service: PipelineEventEmitterService) -> EvaluateStageOutputUseCase:
    return EvaluateStageOutputUseCase(emitter=emitter_service)


class TestQaEvaluationCommand:
    def test_valid_pass_command_constructs(self) -> None:
        # Arrange / Act
        command = QaEvaluationCommand(
            pipeline_run_id="run-001",
            stage_name="research",
            qa_decision="PASS",
            critique_score=90,
        )
        # Assert
        assert command.pipeline_run_id == "run-001"
        assert command.qa_decision == "PASS"

    def test_empty_pipeline_run_id_raises(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id"):
            QaEvaluationCommand(
                pipeline_run_id="",
                stage_name="research",
                qa_decision="PASS",
                critique_score=90,
            )

    def test_invalid_decision_raises(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="qa_decision"):
            QaEvaluationCommand(
                pipeline_run_id="run-001",
                stage_name="research",
                qa_decision="MAYBE",
                critique_score=50,
            )

    def test_score_out_of_range_raises(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="critique_score"):
            QaEvaluationCommand(
                pipeline_run_id="run-001",
                stage_name="research",
                qa_decision="PASS",
                critique_score=101,
            )


class TestEvaluateStageOutputUseCasePassDecision:
    async def test_emits_qa_gate_passed_event(
        self,
        use_case: EvaluateStageOutputUseCase,
        fake_event_store: FakeEventStore,
    ) -> None:
        # Arrange
        command = QaEvaluationCommand(
            pipeline_run_id="run-001",
            stage_name="research",
            qa_decision="PASS",
            critique_score=92,
        )

        # Act
        await use_case.execute(command)

        # Assert
        passed_events = fake_event_store.events_of_type(QA_GATE_PASSED)
        assert len(passed_events) == 1
        event = passed_events[0]
        assert event.data["pipeline_run_id"] == "run-001"
        assert event.data["stage_name"] == "research"
        assert event.data["critique_score"] == 92

    async def test_emits_no_rework_or_fail_events_on_pass(
        self,
        use_case: EvaluateStageOutputUseCase,
        fake_event_store: FakeEventStore,
    ) -> None:
        # Arrange
        command = QaEvaluationCommand(
            pipeline_run_id="run-001",
            stage_name="research",
            qa_decision="PASS",
            critique_score=85,
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert len(fake_event_store.events_of_type(QA_GATE_REWORK)) == 0
        assert len(fake_event_store.events_of_type(QA_GATE_FAILED)) == 0


class TestEvaluateStageOutputUseCaseReworkDecision:
    async def test_emits_qa_gate_rework_event(
        self,
        use_case: EvaluateStageOutputUseCase,
        fake_event_store: FakeEventStore,
    ) -> None:
        # Arrange
        command = QaEvaluationCommand(
            pipeline_run_id="run-002",
            stage_name="transcript",
            qa_decision="REWORK",
            critique_score=60,
        )

        # Act
        await use_case.execute(command)

        # Assert
        rework_events = fake_event_store.events_of_type(QA_GATE_REWORK)
        assert len(rework_events) == 1
        assert rework_events[0].data["qa_decision"] == "REWORK"
        assert rework_events[0].data["critique_score"] == 60


class TestEvaluateStageOutputUseCaseFailDecision:
    async def test_emits_qa_gate_failed_event(
        self,
        use_case: EvaluateStageOutputUseCase,
        fake_event_store: FakeEventStore,
    ) -> None:
        # Arrange
        command = QaEvaluationCommand(
            pipeline_run_id="run-003",
            stage_name="content",
            qa_decision="FAIL",
            critique_score=15,
        )

        # Act
        await use_case.execute(command)

        # Assert
        failed_events = fake_event_store.events_of_type(QA_GATE_FAILED)
        assert len(failed_events) == 1
        assert failed_events[0].data["stage_name"] == "content"

    async def test_each_decision_maps_to_correct_event_type(
        self,
        use_case: EvaluateStageOutputUseCase,
        fake_event_store: FakeEventStore,
    ) -> None:
        # Arrange
        pass_command = QaEvaluationCommand("run-x", "router", "PASS", 90)
        rework_command = QaEvaluationCommand("run-x", "router", "REWORK", 60)
        fail_command = QaEvaluationCommand("run-x", "router", "FAIL", 20)

        # Act
        await use_case.execute(pass_command)
        await use_case.execute(rework_command)
        await use_case.execute(fail_command)

        # Assert
        assert len(fake_event_store.events_of_type(QA_GATE_PASSED)) == 1
        assert len(fake_event_store.events_of_type(QA_GATE_REWORK)) == 1
        assert len(fake_event_store.events_of_type(QA_GATE_FAILED)) == 1
        assert len(fake_event_store.events) == 3
