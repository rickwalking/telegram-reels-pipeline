"""Unit tests for EscalatePipelineRunUseCase."""

from __future__ import annotations

import contextlib

import pytest

from pipeline.application.use_cases.escalate_pipeline_run_use_case import (
    EscalatePipelineRunUseCase,
    EscalationCommand,
)
from pipeline.domain.event_types import (
    ESCALATION_LAYOUT_UNKNOWN,
    ESCALATION_QA_EXHAUSTED,
    PIPELINE_PAUSED,
)
from tests.fakes.fake_event_emitter import make_fake_event_emitter


class TestEscalatePipelineRunUseCaseLayoutUnknown:
    async def test_emits_escalation_layout_unknown_event(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-layout-001")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-layout-001",
            escalation_reason="layout_unknown",
            stage_name="layout_detective",
        )

        # Act
        await use_case.execute(command)

        # Assert
        event_types = [event.event_type for event in emitter.emitted_events]
        assert ESCALATION_LAYOUT_UNKNOWN in event_types

    async def test_emits_pipeline_paused_after_layout_unknown(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-layout-002")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-layout-002",
            escalation_reason="layout_unknown",
            stage_name="layout_detective",
        )

        # Act
        await use_case.execute(command)

        # Assert
        event_types = [event.event_type for event in emitter.emitted_events]
        assert PIPELINE_PAUSED in event_types

    async def test_layout_unknown_emits_exactly_two_events(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-layout-003")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-layout-003",
            escalation_reason="layout_unknown",
            stage_name="layout_detective",
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert len(emitter.emitted_events) == 2

    async def test_projection_execution_status_is_paused_after_layout_unknown(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-layout-004")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-layout-004",
            escalation_reason="layout_unknown",
            stage_name="layout_detective",
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert emitter.projection.execution_status == "paused"

    async def test_projection_escalation_status_reflects_layout_unknown(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-layout-005")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-layout-005",
            escalation_reason="layout_unknown",
            stage_name="layout_detective",
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert emitter.projection.escalation_status == "layout_unknown"


class TestEscalatePipelineRunUseCaseQaExhausted:
    async def test_emits_escalation_qa_exhausted_event(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-qa-001")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-qa-001",
            escalation_reason="qa_exhausted",
            stage_name="transcript",
        )

        # Act
        await use_case.execute(command)

        # Assert
        event_types = [event.event_type for event in emitter.emitted_events]
        assert ESCALATION_QA_EXHAUSTED in event_types

    async def test_emits_pipeline_paused_after_qa_exhausted(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-qa-002")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-qa-002",
            escalation_reason="qa_exhausted",
            stage_name="transcript",
        )

        # Act
        await use_case.execute(command)

        # Assert
        event_types = [event.event_type for event in emitter.emitted_events]
        assert PIPELINE_PAUSED in event_types

    async def test_escalation_event_precedes_paused_event(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-qa-003")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-qa-003",
            escalation_reason="qa_exhausted",
            stage_name="transcript",
        )

        # Act
        await use_case.execute(command)

        # Assert
        event_types = [event.event_type for event in emitter.emitted_events]
        assert event_types.index(ESCALATION_QA_EXHAUSTED) < event_types.index(PIPELINE_PAUSED)

    async def test_projection_escalation_status_reflects_qa_exhausted(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-qa-004")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-qa-004",
            escalation_reason="qa_exhausted",
            stage_name="transcript",
        )

        # Act
        await use_case.execute(command)

        # Assert
        assert emitter.projection.escalation_status == "qa_exhausted"


class TestEscalatePipelineRunUseCaseUnknownReason:
    async def test_unknown_reason_raises_value_error(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-unknown-001")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-unknown-001",
            escalation_reason="completely_invalid_reason",
            stage_name="router",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown escalation_reason"):
            await use_case.execute(command)

    async def test_unknown_reason_emits_no_events(self) -> None:
        # Arrange
        emitter = make_fake_event_emitter("run-unknown-002")
        use_case = EscalatePipelineRunUseCase(event_emitter=emitter)
        command = EscalationCommand(
            pipeline_run_id="run-unknown-002",
            escalation_reason="not_a_real_reason",
            stage_name="router",
        )

        # Act
        with contextlib.suppress(ValueError):
            await use_case.execute(command)

        # Assert
        assert len(emitter.emitted_events) == 0
