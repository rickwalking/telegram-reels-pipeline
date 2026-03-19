"""Unit tests for stage_output_mappers — DTO to event payload conversion."""

from __future__ import annotations

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO
from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO
from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO
from pipeline.presentation.dtos.layout_analysis_output_dto import LayoutAnalysisOutputDTO
from pipeline.presentation.dtos.mappers.stage_output_mappers import (
    map_assembly_report_dto_to_event_payload,
    map_content_dto_to_event_payload,
    map_ffmpeg_encoding_plan_dto_to_event_payload,
    map_layout_analysis_dto_to_event_payload,
    map_research_dto_to_event_payload,
    map_router_dto_to_event_payload,
    map_transcript_dto_to_event_payload,
)
from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO
from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO
from pipeline.presentation.dtos.transcript_output_dto import TranscriptOutputDTO


class TestMapRouterDtoToEventPayload:
    def test_all_fields_are_present_in_payload(self) -> None:
        # Arrange
        dto = RouterOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="router",
            generated_at="2026-03-16T10:00:00Z",
            tier="short",
            topic_focus="AI safety",
            elicitation_answers={"tone": "casual"},
            style_preference="auto",
        )

        # Act
        payload = map_router_dto_to_event_payload(dto)

        # Assert
        assert payload["pipeline_run_id"] == "run-abc"
        assert payload["stage_name"] == "router"
        assert payload["tier"] == "short"
        assert payload["topic_focus"] == "AI safety"
        assert payload["elicitation_answers"] == {"tone": "casual"}
        assert payload["style_preference"] == "auto"

    def test_payload_is_a_plain_dict(self) -> None:
        # Arrange
        dto = RouterOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="router",
            generated_at="2026-03-16T10:00:00Z",
            tier="short",
            topic_focus="topic",
            elicitation_answers={},
        )

        # Act
        payload = map_router_dto_to_event_payload(dto)

        # Assert
        assert isinstance(payload, dict)


class TestMapResearchDtoToEventPayload:
    def test_all_fields_are_present_in_payload(self) -> None:
        # Arrange
        dto = ResearchOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="research",
            generated_at="2026-03-16T10:00:00Z",
            episode_title="AI Podcast",
            channel_name="TechCast",
            episode_duration_seconds=3600.0,
            context_summary="Great episode",
            key_topics=["AI", "safety"],
        )

        # Act
        payload = map_research_dto_to_event_payload(dto)

        # Assert
        assert payload["episode_title"] == "AI Podcast"
        assert payload["channel_name"] == "TechCast"
        assert payload["episode_duration_seconds"] == 3600.0
        assert payload["key_topics"] == ["AI", "safety"]


class TestMapTranscriptDtoToEventPayload:
    def test_moments_are_serialized_as_list_of_dicts(self) -> None:
        # Arrange
        dto = TranscriptOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="transcript",
            generated_at="2026-03-16T10:00:00Z",
            moments=[
                {
                    "moment_start_seconds": 10.0,
                    "moment_end_seconds": 70.0,
                    "selected_quote": "Quote text",
                    "narrative_role": "core",
                    "selection_reasoning": "Best moment",
                }
            ],  # type: ignore[arg-type]
        )

        # Act
        payload = map_transcript_dto_to_event_payload(dto)

        # Assert
        moments = payload["moments"]
        assert isinstance(moments, list)
        assert len(moments) == 1  # type: ignore[arg-type]
        first_moment = moments[0]  # type: ignore[index]
        assert first_moment["moment_start_seconds"] == 10.0  # type: ignore[index]
        assert first_moment["narrative_role"] == "core"  # type: ignore[index]

    def test_empty_moments_list_produces_empty_list_in_payload(self) -> None:
        # Arrange
        dto = TranscriptOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="transcript",
            generated_at="2026-03-16T10:00:00Z",
            moments=[],
        )

        # Act
        payload = map_transcript_dto_to_event_payload(dto)

        # Assert
        assert payload["moments"] == []


class TestMapContentDtoToEventPayload:
    def test_all_fields_are_present_in_payload(self) -> None:
        # Arrange
        dto = ContentOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="content",
            generated_at="2026-03-16T10:00:00Z",
            description_options=["Desc A", "Desc B"],
            hashtag_sets=[["#AI"], ["#tech"]],
            music_suggestions=["Lo-fi"],
        )

        # Act
        payload = map_content_dto_to_event_payload(dto)

        # Assert
        assert payload["description_options"] == ["Desc A", "Desc B"]
        assert payload["hashtag_sets"] == [["#AI"], ["#tech"]]
        assert payload["music_suggestions"] == ["Lo-fi"]


class TestMapLayoutAnalysisDtoToEventPayload:
    def test_face_positions_are_serialized_as_list_of_dicts(self) -> None:
        # Arrange
        dto = LayoutAnalysisOutputDTO(
            pipeline_run_id="run-abc",
            stage_name="layout_detective",
            generated_at="2026-03-16T10:00:00Z",
            layout_classification="duo_split",
            face_positions=[
                {
                    "frame_index": 0,
                    "face_x": 100,
                    "face_y": 200,
                    "face_width": 150,
                    "face_height": 180,
                    "confidence": 0.95,
                }
            ],  # type: ignore[arg-type]
            framing_style_recommendation="split_horizontal",
        )

        # Act
        payload = map_layout_analysis_dto_to_event_payload(dto)

        # Assert
        assert payload["layout_classification"] == "duo_split"
        face_positions = payload["face_positions"]
        assert isinstance(face_positions, list)
        assert len(face_positions) == 1  # type: ignore[arg-type]


class TestMapFfmpegEncodingPlanDtoToEventPayload:
    def test_segments_are_serialized_as_list_of_dicts(self) -> None:
        # Arrange
        dto = FfmpegEncodingPlanDTO(
            pipeline_run_id="run-abc",
            stage_name="ffmpeg_engineer",
            generated_at="2026-03-16T10:00:00Z",
            segments=[
                {
                    "start_seconds": 0.0,
                    "end_seconds": 30.0,
                    "crop_x": 0,
                    "crop_y": 0,
                    "crop_width": 1080,
                    "crop_height": 1920,
                    "framing_style": "solo",
                }
            ],  # type: ignore[arg-type]
        )

        # Act
        payload = map_ffmpeg_encoding_plan_dto_to_event_payload(dto)

        # Assert
        assert payload["codec"] == "libx264"
        assert payload["bitrate"] == "4M"
        segments = payload["segments"]
        assert isinstance(segments, list)
        assert len(segments) == 1  # type: ignore[arg-type]

    def test_default_values_are_included_in_payload(self) -> None:
        # Arrange
        dto = FfmpegEncodingPlanDTO(
            pipeline_run_id="run-abc",
            stage_name="ffmpeg_engineer",
            generated_at="2026-03-16T10:00:00Z",
            segments=[],
        )

        # Act
        payload = map_ffmpeg_encoding_plan_dto_to_event_payload(dto)

        # Assert
        assert payload["thread_count"] == 2
        assert payload["output_resolution"] == "1080x1920"


class TestMapAssemblyReportDtoToEventPayload:
    def test_all_fields_are_present_in_payload(self) -> None:
        # Arrange
        dto = AssemblyReportDTO(
            pipeline_run_id="run-abc",
            stage_name="assembly",
            generated_at="2026-03-16T10:00:00Z",
            final_reel_path="/workspace/final-reel.mp4",
            total_duration_seconds=58.5,
            segment_count=3,
            quality_score=0.92,
        )

        # Act
        payload = map_assembly_report_dto_to_event_payload(dto)

        # Assert
        assert payload["final_reel_path"] == "/workspace/final-reel.mp4"
        assert payload["total_duration_seconds"] == 58.5
        assert payload["segment_count"] == 3
        assert payload["quality_score"] == 0.92
        assert payload["pipeline_run_id"] == "run-abc"
