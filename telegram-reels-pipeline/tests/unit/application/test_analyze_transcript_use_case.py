"""Unit tests for AnalyzeTranscriptUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.use_cases.analyze_transcript_use_case import (
    AnalyzeTranscriptCommand,
    AnalyzeTranscriptUseCase,
)
from pipeline.domain import event_types


def _make_use_case() -> tuple[AnalyzeTranscriptUseCase, MagicMock]:
    """Build a use case with a fake event emitter."""
    event_emitter = MagicMock()
    event_emitter.emit_stage_entered = AsyncMock()
    event_emitter.emit_stage_completed = AsyncMock()
    event_emitter.emit_stage_failed = AsyncMock()
    use_case = AnalyzeTranscriptUseCase(event_emitter=event_emitter)
    return use_case, event_emitter


class TestAnalyzeTranscriptUseCaseEmitsStageEntered:
    async def test_emits_stage_entered_with_correct_pipeline_run_id(self) -> None:
        # Arrange
        use_case, event_emitter = _make_use_case()
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-abc-123")

        # Act
        await use_case.execute(command)

        # Assert
        event_emitter.emit_stage_entered.assert_awaited_once_with(
            pipeline_run_id="run-abc-123",
            stage_name="transcript",
        )

    async def test_emits_stage_entered_with_custom_stage_name(self) -> None:
        # Arrange
        use_case, event_emitter = _make_use_case()
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-xyz", stage_name="custom-transcript")

        # Act
        await use_case.execute(command)

        # Assert
        event_emitter.emit_stage_entered.assert_awaited_once_with(
            pipeline_run_id="run-xyz",
            stage_name="custom-transcript",
        )


class TestAnalyzeTranscriptUseCaseEmitsStageCompleted:
    async def test_emits_stage_completed_with_correct_pipeline_run_id(self) -> None:
        # Arrange
        use_case, event_emitter = _make_use_case()
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-abc-123")

        # Act
        await use_case.execute(command)

        # Assert
        event_emitter.emit_stage_completed.assert_awaited_once_with(
            pipeline_run_id="run-abc-123",
            stage_name="transcript",
        )

    async def test_stage_completed_emitted_after_stage_entered(self) -> None:
        # Arrange
        call_order: list[str] = []

        event_emitter = MagicMock()
        event_emitter.emit_stage_entered = AsyncMock(
            side_effect=lambda **_kwargs: call_order.append(event_types.STAGE_ENTERED)
        )
        event_emitter.emit_stage_completed = AsyncMock(
            side_effect=lambda **_kwargs: call_order.append(event_types.STAGE_COMPLETED)
        )

        use_case = AnalyzeTranscriptUseCase(event_emitter=event_emitter)
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-order-test")

        # Act
        await use_case.execute(command)

        # Assert
        assert call_order == [event_types.STAGE_ENTERED, event_types.STAGE_COMPLETED]


class TestAnalyzeTranscriptCommand:
    def test_default_stage_name_is_transcript(self) -> None:
        # Arrange / Act
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-001")

        # Assert
        assert command.stage_name == "transcript"

    def test_command_is_frozen(self) -> None:
        # Arrange
        command = AnalyzeTranscriptCommand(pipeline_run_id="run-001")

        # Act / Assert
        with pytest.raises(AttributeError):
            command.pipeline_run_id = "mutated"  # type: ignore[misc]
