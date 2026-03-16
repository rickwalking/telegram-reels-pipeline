"""Tests for domain event models — construction, validation, and immutability."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from pipeline.domain.events import CreatePipelineRunCommand, PipelineStateEvent, RunStateProjection


class TestPipelineStateEvent:
    def test_construction_with_valid_data_creates_event(self) -> None:
        # Arrange
        payload = {"stage": "router", "attempt": 1}

        # Act
        event = PipelineStateEvent(
            event_id="evt-001",
            pipeline_run_id="run-abc",
            event_type="pipeline.stage_entered",
            stage_name="router",
            payload_data=payload,
            created_at="2026-03-16T10:00:00Z",
        )

        # Assert
        assert event.event_id == "evt-001"
        assert event.pipeline_run_id == "run-abc"
        assert event.event_type == "pipeline.stage_entered"
        assert event.stage_name == "router"
        assert event.created_at == "2026-03-16T10:00:00Z"

    def test_empty_event_id_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="event_id must not be empty"):
            PipelineStateEvent(
                event_id="",
                pipeline_run_id="run-abc",
                event_type="pipeline.stage_entered",
                stage_name="router",
                payload_data={},
                created_at="2026-03-16T10:00:00Z",
            )

    def test_empty_pipeline_run_id_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id must not be empty"):
            PipelineStateEvent(
                event_id="evt-001",
                pipeline_run_id="",
                event_type="pipeline.stage_entered",
                stage_name="router",
                payload_data={},
                created_at="2026-03-16T10:00:00Z",
            )

    def test_empty_event_type_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="event_type must not be empty"):
            PipelineStateEvent(
                event_id="evt-001",
                pipeline_run_id="run-abc",
                event_type="",
                stage_name="router",
                payload_data={},
                created_at="2026-03-16T10:00:00Z",
            )

    def test_empty_created_at_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="created_at must not be empty"):
            PipelineStateEvent(
                event_id="evt-001",
                pipeline_run_id="run-abc",
                event_type="pipeline.stage_entered",
                stage_name="router",
                payload_data={},
                created_at="",
            )

    def test_plain_dict_payload_is_coerced_to_mapping_proxy_type(self) -> None:
        # Arrange
        plain_dict_payload = {"key": "value", "count": 42}

        # Act
        event = PipelineStateEvent(
            event_id="evt-001",
            pipeline_run_id="run-abc",
            event_type="pipeline.stage_entered",
            stage_name="router",
            payload_data=plain_dict_payload,
            created_at="2026-03-16T10:00:00Z",
        )

        # Assert
        assert isinstance(event.payload_data, MappingProxyType)

    def test_mapping_proxy_type_payload_is_preserved_unchanged(self) -> None:
        # Arrange
        immutable_payload: MappingProxyType[str, object] = MappingProxyType({"key": "value"})

        # Act
        event = PipelineStateEvent(
            event_id="evt-001",
            pipeline_run_id="run-abc",
            event_type="pipeline.stage_entered",
            stage_name="router",
            payload_data=immutable_payload,
            created_at="2026-03-16T10:00:00Z",
        )

        # Assert
        assert event.payload_data is immutable_payload

    def test_frozen_instance_prevents_attribute_reassignment(self) -> None:
        # Arrange
        event = PipelineStateEvent(
            event_id="evt-001",
            pipeline_run_id="run-abc",
            event_type="pipeline.stage_entered",
            stage_name="router",
            payload_data={},
            created_at="2026-03-16T10:00:00Z",
        )

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            event.event_id = "evt-modified"  # type: ignore[misc]

    def test_empty_stage_name_is_allowed(self) -> None:
        # Arrange / Act
        event = PipelineStateEvent(
            event_id="evt-001",
            pipeline_run_id="run-abc",
            event_type="pipeline.run_created",
            stage_name="",
            payload_data={},
            created_at="2026-03-16T10:00:00Z",
        )

        # Assert
        assert event.stage_name == ""


class TestRunStateProjection:
    def test_construction_with_valid_data_creates_projection(self) -> None:
        # Arrange / Act
        projection = RunStateProjection(
            pipeline_run_id="run-001",
            youtube_url="https://youtube.com/watch?v=abc123",
            trigger_source="web_ui",
            current_stage="router",
            execution_status="in_progress",
            current_attempt_count=1,
            qa_evaluation_status="pending",
            completed_stages=("research",),
            escalation_status="none",
            created_at="2026-03-16T10:00:00Z",
            last_updated_at="2026-03-16T10:05:00Z",
        )

        # Assert
        assert projection.pipeline_run_id == "run-001"
        assert projection.youtube_url == "https://youtube.com/watch?v=abc123"
        assert projection.current_attempt_count == 1
        assert projection.completed_stages == ("research",)

    def test_empty_pipeline_run_id_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="pipeline_run_id must not be empty"):
            RunStateProjection(
                pipeline_run_id="",
                youtube_url="https://youtube.com/watch?v=abc123",
                trigger_source="web_ui",
                current_stage="router",
                execution_status="in_progress",
                current_attempt_count=0,
                qa_evaluation_status="pending",
                completed_stages=(),
                escalation_status="none",
                created_at="2026-03-16T10:00:00Z",
                last_updated_at="2026-03-16T10:00:00Z",
            )

    def test_empty_youtube_url_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="youtube_url must not be empty"):
            RunStateProjection(
                pipeline_run_id="run-001",
                youtube_url="",
                trigger_source="web_ui",
                current_stage="router",
                execution_status="in_progress",
                current_attempt_count=0,
                qa_evaluation_status="pending",
                completed_stages=(),
                escalation_status="none",
                created_at="2026-03-16T10:00:00Z",
                last_updated_at="2026-03-16T10:00:00Z",
            )

    def test_negative_attempt_count_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="current_attempt_count must not be negative"):
            RunStateProjection(
                pipeline_run_id="run-001",
                youtube_url="https://youtube.com/watch?v=abc123",
                trigger_source="web_ui",
                current_stage="router",
                execution_status="in_progress",
                current_attempt_count=-1,
                qa_evaluation_status="pending",
                completed_stages=(),
                escalation_status="none",
                created_at="2026-03-16T10:00:00Z",
                last_updated_at="2026-03-16T10:00:00Z",
            )

    def test_zero_attempt_count_is_valid(self) -> None:
        # Arrange / Act
        projection = RunStateProjection(
            pipeline_run_id="run-001",
            youtube_url="https://youtube.com/watch?v=abc123",
            trigger_source="web_ui",
            current_stage="router",
            execution_status="pending",
            current_attempt_count=0,
            qa_evaluation_status="pending",
            completed_stages=(),
            escalation_status="none",
            created_at="2026-03-16T10:00:00Z",
            last_updated_at="2026-03-16T10:00:00Z",
        )

        # Assert
        assert projection.current_attempt_count == 0

    def test_frozen_instance_prevents_attribute_reassignment(self) -> None:
        # Arrange
        projection = RunStateProjection(
            pipeline_run_id="run-001",
            youtube_url="https://youtube.com/watch?v=abc123",
            trigger_source="web_ui",
            current_stage="router",
            execution_status="in_progress",
            current_attempt_count=0,
            qa_evaluation_status="pending",
            completed_stages=(),
            escalation_status="none",
            created_at="2026-03-16T10:00:00Z",
            last_updated_at="2026-03-16T10:00:00Z",
        )

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            projection.execution_status = "completed"  # type: ignore[misc]


class TestCreatePipelineRunCommand:
    def test_construction_with_valid_data_creates_command(self) -> None:
        # Arrange / Act
        command = CreatePipelineRunCommand(
            youtube_url="https://youtube.com/watch?v=abc123",
            topic_focus="AI trends in 2026",
            trigger_source="web_ui",
            client_identifier="user-session-42",
        )

        # Assert
        assert command.youtube_url == "https://youtube.com/watch?v=abc123"
        assert command.topic_focus == "AI trends in 2026"
        assert command.trigger_source == "web_ui"
        assert command.client_identifier == "user-session-42"

    def test_empty_youtube_url_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="youtube_url must not be empty"):
            CreatePipelineRunCommand(
                youtube_url="",
                topic_focus="AI trends",
                trigger_source="web_ui",
                client_identifier="user-42",
            )

    def test_empty_trigger_source_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="trigger_source must not be empty"):
            CreatePipelineRunCommand(
                youtube_url="https://youtube.com/watch?v=abc123",
                topic_focus="AI trends",
                trigger_source="",
                client_identifier="user-42",
            )

    def test_empty_topic_focus_is_allowed(self) -> None:
        # Arrange / Act
        command = CreatePipelineRunCommand(
            youtube_url="https://youtube.com/watch?v=abc123",
            topic_focus="",
            trigger_source="cli",
            client_identifier="local",
        )

        # Assert
        assert command.topic_focus == ""

    def test_frozen_instance_prevents_attribute_reassignment(self) -> None:
        # Arrange
        command = CreatePipelineRunCommand(
            youtube_url="https://youtube.com/watch?v=abc123",
            topic_focus="AI trends",
            trigger_source="web_ui",
            client_identifier="user-42",
        )

        # Act / Assert
        with pytest.raises(FrozenInstanceError):
            command.youtube_url = "https://youtube.com/watch?v=other"  # type: ignore[misc]
