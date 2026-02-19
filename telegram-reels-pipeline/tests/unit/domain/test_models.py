"""Tests for domain models — frozen dataclass construction, immutability, and validation."""

from datetime import datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from pipeline.domain.enums import EscalationState, NarrativeRole, PipelineStage, QADecision, QAStatus, ShotType
from pipeline.domain.models import (
    AgentRequest,
    AgentResult,
    CropRegion,
    FaceGateConfig,
    FaceGateResult,
    LocalizedDescription,
    NarrativeMoment,
    PipelineEvent,
    PublishingAssets,
    QACritique,
    QueueItem,
    RunState,
    Veo3Prompt,
    Veo3PromptVariant,
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


class TestVeo3Prompt:
    def test_construction(self) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Cinematic slow-motion shot")
        assert prompt.variant == "broll"
        assert prompt.prompt == "Cinematic slow-motion shot"

    def test_invalid_variant_raises(self) -> None:
        with pytest.raises(ValueError, match="variant must be one of"):
            Veo3Prompt(variant="invalid", prompt="Some prompt")

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt must not be empty"):
            Veo3Prompt(variant="broll", prompt="")

    def test_whitespace_only_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="prompt must not be empty"):
            Veo3Prompt(variant="broll", prompt="   ")

    def test_all_variant_types(self) -> None:
        for variant in Veo3PromptVariant:
            prompt = Veo3Prompt(variant=variant.value, prompt="test prompt")
            assert prompt.variant == variant.value


class TestLocalizedDescription:
    def test_construction(self) -> None:
        desc = LocalizedDescription(language="pt-BR", text="Descricao do video")
        assert desc.language == "pt-BR"
        assert desc.text == "Descricao do video"

    def test_empty_language_raises(self) -> None:
        with pytest.raises(ValueError, match="language must not be empty"):
            LocalizedDescription(language="", text="Some text")

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text must not be empty"):
            LocalizedDescription(language="pt-BR", text="")

    def test_whitespace_only_language_raises(self) -> None:
        with pytest.raises(ValueError, match="language must not be empty"):
            LocalizedDescription(language="   ", text="Some text")

    def test_whitespace_only_text_raises(self) -> None:
        with pytest.raises(ValueError, match="text must not be empty"):
            LocalizedDescription(language="pt-BR", text="   ")


class TestPublishingAssets:
    @pytest.fixture
    def valid_assets(self) -> PublishingAssets:
        return PublishingAssets(
            descriptions=(LocalizedDescription(language="pt-BR", text="Descricao 1"),),
            hashtags=("#podcast",),
            veo3_prompts=(Veo3Prompt(variant="broll", prompt="Cinematic shot"),),
        )

    def test_construction(self, valid_assets: PublishingAssets) -> None:
        assert len(valid_assets.descriptions) == 1
        assert len(valid_assets.hashtags) == 1
        assert len(valid_assets.veo3_prompts) == 1

    def test_frozen_immutability(self, valid_assets: PublishingAssets) -> None:
        with pytest.raises(AttributeError):
            valid_assets.descriptions = ()  # type: ignore[misc]

    def test_empty_descriptions_raises(self) -> None:
        with pytest.raises(ValueError, match="descriptions must not be empty"):
            PublishingAssets(
                descriptions=(),
                hashtags=("#test",),
                veo3_prompts=(Veo3Prompt(variant="broll", prompt="test"),),
            )

    def test_empty_hashtags_raises(self) -> None:
        with pytest.raises(ValueError, match="hashtags must not be empty"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=(),
                veo3_prompts=(Veo3Prompt(variant="broll", prompt="test"),),
            )

    def test_empty_veo3_prompts_raises(self) -> None:
        with pytest.raises(ValueError, match="veo3_prompts must not be empty"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("#test",),
                veo3_prompts=(),
            )

    def test_more_than_four_prompts_raises(self) -> None:
        five_prompts = (
            Veo3Prompt(variant="broll", prompt="p1"),
            Veo3Prompt(variant="intro", prompt="p2"),
            Veo3Prompt(variant="outro", prompt="p3"),
            Veo3Prompt(variant="transition", prompt="p4"),
            Veo3Prompt(variant="broll", prompt="p5"),
        )
        with pytest.raises(ValueError, match="1-4 items"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("#test",),
                veo3_prompts=five_prompts,
            )

    def test_duplicate_variants_raises(self) -> None:
        with pytest.raises(ValueError, match="unique variants"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("#test",),
                veo3_prompts=(
                    Veo3Prompt(variant="broll", prompt="p1"),
                    Veo3Prompt(variant="broll", prompt="p2"),
                ),
            )

    def test_missing_broll_raises(self) -> None:
        with pytest.raises(ValueError, match="broll"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("#test",),
                veo3_prompts=(Veo3Prompt(variant="intro", prompt="test"),),
            )

    def test_four_unique_variants_valid(self) -> None:
        assets = PublishingAssets(
            descriptions=(LocalizedDescription(language="pt-BR", text="text"),),
            hashtags=("#podcast",),
            veo3_prompts=(
                Veo3Prompt(variant="intro", prompt="p1"),
                Veo3Prompt(variant="broll", prompt="p2"),
                Veo3Prompt(variant="outro", prompt="p3"),
                Veo3Prompt(variant="transition", prompt="p4"),
            ),
        )
        assert len(assets.veo3_prompts) == 4

    def test_hashtag_missing_hash_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="must start with '#'"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("podcast",),
                veo3_prompts=(Veo3Prompt(variant="broll", prompt="test"),),
            )

    def test_hashtag_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            PublishingAssets(
                descriptions=(LocalizedDescription(language="en", text="text"),),
                hashtags=("   ",),
                veo3_prompts=(Veo3Prompt(variant="broll", prompt="test"),),
            )

    def test_whitespace_stripped_on_construction(self) -> None:
        prompt = Veo3Prompt(variant="  broll  ", prompt="  cinematic shot  ")
        assert prompt.variant == "broll"
        assert prompt.prompt == "cinematic shot"

        desc = LocalizedDescription(language="  pt-BR  ", text="  descricao  ")
        assert desc.language == "pt-BR"
        assert desc.text == "descricao"

        assets = PublishingAssets(
            descriptions=(desc,),
            hashtags=("  #podcast  ", "  #tech  "),
            veo3_prompts=(prompt,),
        )
        assert assets.hashtags == ("#podcast", "#tech")


class TestNarrativeMoment:
    def test_construction(self) -> None:
        moment = NarrativeMoment(
            start_seconds=51.0,
            end_seconds=81.0,
            role=NarrativeRole.CORE,
            transcript_excerpt="AI personalities discussion",
        )
        assert moment.duration_seconds == 30.0
        assert moment.role == NarrativeRole.CORE

    def test_negative_start_raises(self) -> None:
        with pytest.raises(ValueError, match="start_seconds"):
            NarrativeMoment(
                start_seconds=-1.0,
                end_seconds=10.0,
                role=NarrativeRole.INTRO,
                transcript_excerpt="text",
            )

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end_seconds"):
            NarrativeMoment(
                start_seconds=50.0,
                end_seconds=40.0,
                role=NarrativeRole.CORE,
                transcript_excerpt="text",
            )

    def test_empty_transcript_raises(self) -> None:
        with pytest.raises(ValueError, match="transcript_excerpt"):
            NarrativeMoment(
                start_seconds=10.0,
                end_seconds=30.0,
                role=NarrativeRole.BUILDUP,
                transcript_excerpt="",
            )

    def test_frozen_immutability(self) -> None:
        moment = NarrativeMoment(
            start_seconds=0.0,
            end_seconds=15.0,
            role=NarrativeRole.INTRO,
            transcript_excerpt="intro text",
        )
        with pytest.raises(AttributeError):
            moment.role = NarrativeRole.CORE  # type: ignore[misc]


class TestFaceGateConfigModel:
    def test_default_weights_sum(self) -> None:
        config = FaceGateConfig()
        total = (
            config.w_area
            + config.w_geometry
            + config.w_separation
            + config.w_vertical
            + config.w_size_ratio
            + config.w_confidence
        )
        assert abs(total - 1.0) < 0.01

    def test_frozen_immutability(self) -> None:
        config = FaceGateConfig()
        with pytest.raises(AttributeError):
            config.min_area_pct = 2.0  # type: ignore[misc]


class TestFaceGateResultModel:
    def test_construction(self) -> None:
        result = FaceGateResult(
            raw_face_count=2,
            editorial_face_count=2,
            duo_score=0.85,
            ema_score=0.72,
            is_editorial_duo=True,
            shot_type=ShotType.TWO_SHOT,
            gate_reason="editorial_duo",
        )
        assert result.shot_type == ShotType.TWO_SHOT

    def test_frozen_immutability(self) -> None:
        result = FaceGateResult(
            raw_face_count=0,
            editorial_face_count=0,
            duo_score=0.0,
            ema_score=0.0,
            is_editorial_duo=False,
            shot_type=ShotType.WIDE_SHOT,
            gate_reason="no_faces",
        )
        with pytest.raises(AttributeError):
            result.is_editorial_duo = True  # type: ignore[misc]
