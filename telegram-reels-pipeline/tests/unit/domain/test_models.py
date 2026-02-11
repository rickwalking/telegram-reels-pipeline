"""Tests for domain models — frozen dataclass construction, immutability, and validation."""

from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.models import (
    AgentRequest,
    AgentResult,
    CropRegion,
    PipelineEvent,
    QACritique,
    QueueItem,
    RunState,
    VideoMetadata,
)
from pipeline.domain.types import GateName, RunId, SessionId


class TestAgentRequest:
    def test_construction_with_required_fields(self) -> None:
        request = AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=Path("stages/stage-01-router.md"),
            agent_definition=Path("agents/router/agent.md"),
        )
        assert request.stage == PipelineStage.ROUTER
        assert request.prior_artifacts == ()
        assert isinstance(request.elicitation_context, MappingProxyType)
        assert len(request.elicitation_context) == 0
        assert request.attempt_history == ()

    def test_frozen_immutability(self) -> None:
        request = AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=Path("stages/stage-01-router.md"),
            agent_definition=Path("agents/router/agent.md"),
        )
        with pytest.raises(AttributeError):
            request.stage = PipelineStage.RESEARCH  # type: ignore[misc]

    def test_elicitation_context_frozen_to_mapping_proxy(self) -> None:
        request = AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=Path("stages/stage-01-router.md"),
            agent_definition=Path("agents/router/agent.md"),
            elicitation_context={"key": "value"},
        )
        assert isinstance(request.elicitation_context, MappingProxyType)
        assert request.elicitation_context["key"] == "value"


class TestAgentResult:
    def test_construction_with_defaults(self) -> None:
        result = AgentResult(status="success")
        assert result.status == "success"
        assert result.artifacts == ()
        assert result.session_id == SessionId("")
        assert result.duration_seconds == 0.0

    def test_construction_with_all_fields(self) -> None:
        result = AgentResult(
            status="success",
            artifacts=(Path("output/artifact.md"),),
            session_id=SessionId("sess-123"),
            duration_seconds=45.2,
        )
        assert len(result.artifacts) == 1
        assert result.session_id == SessionId("sess-123")

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_seconds"):
            AgentResult(status="success", duration_seconds=-1.0)


class TestQACritique:
    def test_construction(self, sample_qa_critique: QACritique) -> None:
        assert sample_qa_critique.decision == QADecision.PASS
        assert sample_qa_critique.score == 92
        assert sample_qa_critique.confidence == 0.95

    def test_rework_with_blockers(self) -> None:
        critique = QACritique(
            decision=QADecision.REWORK,
            score=45,
            gate=GateName("transcript"),
            attempt=2,
            blockers=({"severity": "high", "description": "Segment too short"},),
            prescriptive_fixes=("Extend segment to minimum 60 seconds",),
            confidence=0.80,
        )
        assert len(critique.blockers) == 1
        assert len(critique.prescriptive_fixes) == 1

    def test_score_over_100_raises(self) -> None:
        with pytest.raises(ValueError, match="score must be 0-100"):
            QACritique(decision=QADecision.PASS, score=101, gate=GateName("router"), attempt=1)

    def test_negative_score_raises(self) -> None:
        with pytest.raises(ValueError, match="score must be 0-100"):
            QACritique(decision=QADecision.PASS, score=-1, gate=GateName("router"), attempt=1)

    def test_confidence_over_1_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            QACritique(decision=QADecision.PASS, score=50, gate=GateName("router"), attempt=1, confidence=1.5)

    def test_zero_attempt_raises(self) -> None:
        with pytest.raises(ValueError, match="attempt must be >= 1"):
            QACritique(decision=QADecision.PASS, score=50, gate=GateName("router"), attempt=0)


class TestCropRegion:
    def test_construction(self) -> None:
        region = CropRegion(x=0, y=0, width=1080, height=1920, layout_name="speaker-focus")
        assert region.width == 1080
        assert region.height == 1920
        assert region.layout_name == "speaker-focus"

    def test_negative_x_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            CropRegion(x=-1, y=0, width=1080, height=1920)

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            CropRegion(x=0, y=0, width=0, height=1920)


class TestVideoMetadata:
    def test_construction(self) -> None:
        metadata = VideoMetadata(
            title="Test Episode",
            duration_seconds=3600.0,
            channel="TestChannel",
            publish_date="2026-01-15",
            description="A test episode",
            url="https://youtube.com/watch?v=test",
        )
        assert metadata.title == "Test Episode"
        assert metadata.duration_seconds == 3600.0

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_seconds must be positive"):
            VideoMetadata(
                title="T",
                duration_seconds=0.0,
                channel="C",
                publish_date="2026-01-01",
                description="D",
                url="https://example.com",
            )

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url must not be empty"):
            VideoMetadata(
                title="T",
                duration_seconds=1.0,
                channel="C",
                publish_date="2026-01-01",
                description="D",
                url="",
            )


class TestQueueItem:
    def test_construction_without_topic(self) -> None:
        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=12345,
            queued_at=datetime(2026, 2, 10, 14, 0, 0),
        )
        assert item.topic_focus is None

    def test_construction_with_topic(self) -> None:
        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=12345,
            queued_at=datetime(2026, 2, 10, 14, 0, 0),
            topic_focus="CAP theorem",
        )
        assert item.topic_focus == "CAP theorem"

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="url must not be empty"):
            QueueItem(url="", telegram_update_id=12345, queued_at=datetime(2026, 2, 10))


class TestRunState:
    def test_construction(self, sample_run_state: RunState) -> None:
        assert sample_run_state.run_id == RunId("2026-02-10-abc123")
        assert sample_run_state.current_stage == PipelineStage.RESEARCH
        assert sample_run_state.escalation_state == EscalationState.NONE

    def test_frozen_immutability(self, sample_run_state: RunState) -> None:
        with pytest.raises(AttributeError):
            sample_run_state.current_stage = PipelineStage.TRANSCRIPT  # type: ignore[misc]

    def test_defaults(self) -> None:
        state = RunState(
            run_id=RunId("test-run"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.ROUTER,
        )
        assert state.current_attempt == 1
        assert state.qa_status == QAStatus.PENDING
        assert state.stages_completed == ()
        assert state.escalation_state == EscalationState.NONE

    def test_empty_run_id_raises(self) -> None:
        with pytest.raises(ValueError, match="run_id must not be empty"):
            RunState(
                run_id=RunId(""),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
            )

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValueError, match="youtube_url must not be empty"):
            RunState(run_id=RunId("test"), youtube_url="", current_stage=PipelineStage.ROUTER)

    def test_zero_attempt_raises(self) -> None:
        with pytest.raises(ValueError, match="current_attempt must be >= 1"):
            RunState(
                run_id=RunId("test"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
                current_attempt=0,
            )


class TestPipelineEvent:
    def test_construction(self, sample_pipeline_event: PipelineEvent) -> None:
        assert sample_pipeline_event.event_name == "pipeline.stage_entered"
        assert sample_pipeline_event.stage == PipelineStage.ROUTER

    def test_event_without_stage(self) -> None:
        event = PipelineEvent(
            timestamp="2026-02-10T14:00:00Z",
            event_name="pipeline.started",
            data={"run_id": "test"},
        )
        assert event.stage is None

    def test_data_frozen_to_mapping_proxy(self) -> None:
        event = PipelineEvent(
            timestamp="2026-02-10T14:00:00Z",
            event_name="pipeline.started",
            data={"key": "value"},
        )
        assert isinstance(event.data, MappingProxyType)

    def test_empty_event_name_raises(self) -> None:
        with pytest.raises(ValueError, match="event_name must not be empty"):
            PipelineEvent(timestamp="2026-02-10T14:00:00Z", event_name="")
