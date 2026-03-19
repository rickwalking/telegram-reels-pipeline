"""Unit tests for DetectCameraLayoutUseCase — event-sourced layout detection."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.use_cases.detect_camera_layout_use_case import (
    UNKNOWN_LAYOUT_NAME,
    DetectCameraLayoutUseCase,
    DetectLayoutCommand,
)
from pipeline.domain import event_types
from pipeline.domain.enums import PipelineStage


def _make_fake_event_emitter() -> MagicMock:
    fake_emitter = MagicMock()
    fake_emitter.emit_stage_entered = AsyncMock()
    fake_emitter.emit_stage_completed = AsyncMock()
    fake_emitter.emit_escalation_requested = AsyncMock()
    return fake_emitter


def _make_use_case(fake_emitter: MagicMock) -> DetectCameraLayoutUseCase:
    return DetectCameraLayoutUseCase(event_emitter=fake_emitter)


def _make_command(pipeline_run_id: str = "run-abc-001") -> DetectLayoutCommand:
    return DetectLayoutCommand(pipeline_run_id=pipeline_run_id)


class TestDetectLayoutCommandValidation:
    def test_empty_pipeline_run_id_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id must not be empty"):
            DetectLayoutCommand(pipeline_run_id="")

    def test_default_stage_name_is_layout_detective(self) -> None:
        # Arrange / Act
        command = DetectLayoutCommand(pipeline_run_id="run-123")

        # Assert
        assert command.stage_name == "layout_detective"

    def test_custom_stage_name_is_preserved(self) -> None:
        # Arrange / Act
        command = DetectLayoutCommand(pipeline_run_id="run-123", stage_name="custom_stage")

        # Assert
        assert command.stage_name == "custom_stage"

    def test_empty_stage_name_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="stage_name must not be empty"):
            DetectLayoutCommand(pipeline_run_id="run-123", stage_name="")


class TestDetectCameraLayoutUseCaseUnknownLayout:
    async def test_emits_stage_entered_before_detection(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command()

        # Act
        await use_case.execute(command)

        # Assert
        fake_emitter.emit_stage_entered.assert_awaited_once_with(
            PipelineStage.LAYOUT_DETECTIVE, "run-abc-001"
        )

    async def test_emits_escalation_event_for_unknown_layout(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command()

        # Act
        await use_case.execute(command)

        # Assert
        fake_emitter.emit_escalation_requested.assert_awaited_once_with(
            PipelineStage.LAYOUT_DETECTIVE, "run-abc-001"
        )

    async def test_does_not_emit_stage_completed_for_unknown_layout(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command()

        # Act
        await use_case.execute(command)

        # Assert
        fake_emitter.emit_stage_completed.assert_not_awaited()

    async def test_escalation_event_uses_layout_detective_stage(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command(pipeline_run_id="run-xyz-999")

        # Act
        await use_case.execute(command)

        # Assert
        call_kwargs = fake_emitter.emit_escalation_requested.call_args
        stage_arg = call_kwargs.args[0]
        assert stage_arg == PipelineStage.LAYOUT_DETECTIVE


class TestDetectCameraLayoutUseCaseKnownLayout:
    async def test_emits_stage_completed_when_layout_is_known(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command()

        with patch.object(use_case, "_detect_layout_placeholder", return_value="duo_split"):
            # Act
            await use_case.execute(command)

        # Assert
        fake_emitter.emit_stage_completed.assert_awaited_once_with(
            PipelineStage.LAYOUT_DETECTIVE, "run-abc-001"
        )

    async def test_does_not_emit_escalation_when_layout_is_known(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command()

        with patch.object(use_case, "_detect_layout_placeholder", return_value="solo"):
            # Act
            await use_case.execute(command)

        # Assert
        fake_emitter.emit_escalation_requested.assert_not_awaited()

    async def test_emits_stage_entered_for_known_layout_too(self) -> None:
        # Arrange
        fake_emitter = _make_fake_event_emitter()
        use_case = _make_use_case(fake_emitter)
        command = _make_command(pipeline_run_id="run-known-001")

        with patch.object(use_case, "_detect_layout_placeholder", return_value="screen_share"):
            # Act
            await use_case.execute(command)

        # Assert
        fake_emitter.emit_stage_entered.assert_awaited_once_with(
            PipelineStage.LAYOUT_DETECTIVE, "run-known-001"
        )


class TestDetectCameraLayoutUseCaseConstants:
    def test_unknown_layout_name_constant_is_unknown(self) -> None:
        # Assert
        assert UNKNOWN_LAYOUT_NAME == "unknown"

    def test_event_types_constants_match_expected_names(self) -> None:
        # Assert
        assert event_types.STAGE_ENTERED == "pipeline.stage_entered"
        assert event_types.STAGE_COMPLETED == "pipeline.stage_completed"
        assert event_types.ESCALATION_REQUESTED == "pipeline.escalation_requested"
