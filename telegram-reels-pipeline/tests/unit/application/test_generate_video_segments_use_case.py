"""Unit tests for GenerateVideoSegmentsUseCase — event-sourced FFmpeg stage wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pipeline.application.event_bus import EventBus
from pipeline.application.services.pipeline_event_emitter_service import PipelineEventEmitterService
from pipeline.application.use_cases.generate_video_segments_use_case import (
    GenerateSegmentsCommand,
    GenerateVideoSegmentsUseCase,
)
from pipeline.domain import event_types
from pipeline.domain.enums import PipelineStage

_RUN_ID = "run-20260318-abc123"


def _make_use_case() -> tuple[GenerateVideoSegmentsUseCase, AsyncMock, AsyncMock]:
    """Build a use case wired to a spy EventBus."""
    event_bus = EventBus()
    event_bus.publish = AsyncMock()  # type: ignore[method-assign]
    emitter = PipelineEventEmitterService(event_bus=event_bus)
    use_case = GenerateVideoSegmentsUseCase(event_emitter=emitter)
    return use_case, event_bus.publish, AsyncMock()


class TestGenerateSegmentsCommand:
    def test_default_stage_name_is_ffmpeg_engineer(self) -> None:
        # Arrange / Act
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Assert
        assert command.stage_name == "ffmpeg_engineer"

    def test_custom_stage_name_is_stored(self) -> None:
        # Arrange / Act
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID, stage_name="custom_stage")

        # Assert
        assert command.stage_name == "custom_stage"

    def test_empty_pipeline_run_id_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id must not be empty"):
            GenerateSegmentsCommand(pipeline_run_id="")

    def test_command_is_immutable(self) -> None:
        # Arrange
        from dataclasses import FrozenInstanceError

        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            command.pipeline_run_id = "mutated"  # type: ignore[misc]


class TestGenerateVideoSegmentsUseCaseEvents:
    async def test_emits_stage_entered_for_ffmpeg_engineer(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        assert any(e.event_name == event_types.STAGE_ENTERED for e in published_events)

    async def test_stage_entered_event_carries_correct_stage(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        entered_event = next(e for e in published_events if e.event_name == event_types.STAGE_ENTERED)
        assert entered_event.stage == PipelineStage.FFMPEG_ENGINEER

    async def test_emits_stage_completed_for_ffmpeg_engineer(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        assert any(e.event_name == event_types.STAGE_COMPLETED for e in published_events)

    async def test_stage_completed_event_carries_correct_stage(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        completed_event = next(e for e in published_events if e.event_name == event_types.STAGE_COMPLETED)
        assert completed_event.stage == PipelineStage.FFMPEG_ENGINEER

    async def test_stage_entered_precedes_stage_completed(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert — entered must be published before completed
        event_names = [spy_call.args[0].event_name for spy_call in publish_spy.call_args_list]
        entered_index = event_names.index(event_types.STAGE_ENTERED)
        completed_index = event_names.index(event_types.STAGE_COMPLETED)
        assert entered_index < completed_index


class TestGenerateVideoSegmentsUseCaseArtifacts:
    async def test_stage_completed_payload_includes_segment_artifact_paths(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        completed_event = next(e for e in published_events if e.event_name == event_types.STAGE_COMPLETED)
        artifact_paths = completed_event.data["artifact_paths"]
        assert len(artifact_paths) > 0

    async def test_segment_paths_contain_pipeline_run_id(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        completed_event = next(e for e in published_events if e.event_name == event_types.STAGE_COMPLETED)
        artifact_paths = completed_event.data["artifact_paths"]
        assert all(_RUN_ID in path for path in artifact_paths)

    async def test_segment_paths_are_mp4_files(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        completed_event = next(e for e in published_events if e.event_name == event_types.STAGE_COMPLETED)
        artifact_paths = completed_event.data["artifact_paths"]
        assert all(path.endswith(".mp4") for path in artifact_paths)

    async def test_completed_event_carries_pipeline_run_id_in_data(self) -> None:
        # Arrange
        use_case, publish_spy, _ = _make_use_case()
        command = GenerateSegmentsCommand(pipeline_run_id=_RUN_ID)

        # Act
        await use_case.execute(command)

        # Assert
        published_events = [spy_call.args[0] for spy_call in publish_spy.call_args_list]
        completed_event = next(e for e in published_events if e.event_name == event_types.STAGE_COMPLETED)
        assert completed_event.data["pipeline_run_id"] == _RUN_ID
