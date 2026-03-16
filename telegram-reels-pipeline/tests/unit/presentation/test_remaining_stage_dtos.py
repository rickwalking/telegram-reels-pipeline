"""Unit tests for ResearchOutputDTO, ContentOutputDTO, LayoutAnalysisOutputDTO,
FfmpegEncodingPlanDTO, AssemblyReportDTO — valid payloads and constraint enforcement."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO
from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO
from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO, VideoSegmentDTO
from pipeline.presentation.dtos.layout_analysis_output_dto import FacePositionItemDTO, LayoutAnalysisOutputDTO
from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO

# ---------------------------------------------------------------------------
# ResearchOutputDTO
# ---------------------------------------------------------------------------


class TestResearchOutputDTO:
    def test_valid_payload_is_accepted(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "research",
            "generated_at": "2026-03-16T10:00:00Z",
            "episode_title": "The Future of AI",
            "channel_name": "TechPodcast",
            "episode_duration_seconds": 3600.0,
            "context_summary": "Episode covering AI breakthroughs",
            "key_topics": ["LLMs", "safety", "alignment"],
        }

        # Act
        dto = ResearchOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.episode_title == "The Future of AI"
        assert dto.channel_name == "TechPodcast"
        assert dto.episode_duration_seconds == 3600.0
        assert dto.key_topics == ["LLMs", "safety", "alignment"]

    def test_extra_field_is_rejected(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "research",
            "generated_at": "2026-03-16T10:00:00Z",
            "episode_title": "The Future of AI",
            "channel_name": "TechPodcast",
            "episode_duration_seconds": 3600.0,
            "context_summary": "Summary",
            "key_topics": ["LLMs"],
            "extra": "forbidden",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            ResearchOutputDTO(**payload)  # type: ignore[arg-type]

    def test_missing_episode_title_raises_validation_error(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "research",
            "generated_at": "2026-03-16T10:00:00Z",
            "channel_name": "TechPodcast",
            "episode_duration_seconds": 3600.0,
            "context_summary": "Summary",
            "key_topics": [],
        }

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            ResearchOutputDTO(**payload)  # type: ignore[arg-type]
        assert "episode_title" in str(excinfo.value)

    def test_empty_key_topics_list_is_valid(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "research",
            "generated_at": "2026-03-16T10:00:00Z",
            "episode_title": "Episode",
            "channel_name": "Channel",
            "episode_duration_seconds": 1800.0,
            "context_summary": "Summary",
            "key_topics": [],
        }

        # Act
        dto = ResearchOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.key_topics == []


# ---------------------------------------------------------------------------
# ContentOutputDTO
# ---------------------------------------------------------------------------


class TestContentOutputDTO:
    def test_valid_payload_is_accepted(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "content",
            "generated_at": "2026-03-16T10:00:00Z",
            "description_options": ["Great episode!", "Must watch!"],
            "hashtag_sets": [["#AI", "#tech"], ["#podcast", "#LLM"]],
            "music_suggestions": ["Lo-fi beats", "Upbeat electronic"],
        }

        # Act
        dto = ContentOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.description_options == ["Great episode!", "Must watch!"]
        assert dto.hashtag_sets == [["#AI", "#tech"], ["#podcast", "#LLM"]]
        assert dto.music_suggestions == ["Lo-fi beats", "Upbeat electronic"]

    def test_extra_field_is_rejected(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "content",
            "generated_at": "2026-03-16T10:00:00Z",
            "description_options": ["Desc"],
            "hashtag_sets": [["#AI"]],
            "music_suggestions": ["beats"],
            "surprise": "rejected",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            ContentOutputDTO(**payload)  # type: ignore[arg-type]

    def test_missing_description_options_raises_validation_error(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "content",
            "generated_at": "2026-03-16T10:00:00Z",
            "hashtag_sets": [["#AI"]],
            "music_suggestions": ["beats"],
        }

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            ContentOutputDTO(**payload)  # type: ignore[arg-type]
        assert "description_options" in str(excinfo.value)


# ---------------------------------------------------------------------------
# LayoutAnalysisOutputDTO
# ---------------------------------------------------------------------------


class TestFacePositionItemDTO:
    def test_valid_face_position_is_accepted(self) -> None:
        # Arrange
        payload = {
            "frame_index": 0,
            "face_x": 100,
            "face_y": 200,
            "face_width": 150,
            "face_height": 180,
            "confidence": 0.95,
        }

        # Act
        dto = FacePositionItemDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.frame_index == 0
        assert dto.confidence == 0.95

    def test_extra_field_on_face_position_is_rejected(self) -> None:
        # Arrange
        payload = {
            "frame_index": 0,
            "face_x": 100,
            "face_y": 200,
            "face_width": 150,
            "face_height": 180,
            "confidence": 0.95,
            "extra": "forbidden",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            FacePositionItemDTO(**payload)  # type: ignore[arg-type]


class TestLayoutAnalysisOutputDTO:
    def test_valid_layout_analysis_is_accepted(self) -> None:
        # Arrange
        face_position = {
            "frame_index": 0,
            "face_x": 100,
            "face_y": 200,
            "face_width": 150,
            "face_height": 180,
            "confidence": 0.92,
        }
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "layout_detective",
            "generated_at": "2026-03-16T10:00:00Z",
            "layout_classification": "duo_split",
            "face_positions": [face_position],
            "framing_style_recommendation": "split_horizontal",
        }

        # Act
        dto = LayoutAnalysisOutputDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.layout_classification == "duo_split"
        assert len(dto.face_positions) == 1
        assert dto.framing_style_recommendation == "split_horizontal"

    def test_extra_field_on_layout_analysis_is_rejected(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "layout_detective",
            "generated_at": "2026-03-16T10:00:00Z",
            "layout_classification": "solo",
            "face_positions": [],
            "framing_style_recommendation": "solo",
            "forbidden_field": True,
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            LayoutAnalysisOutputDTO(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FfmpegEncodingPlanDTO
# ---------------------------------------------------------------------------


class TestVideoSegmentDTO:
    def test_valid_segment_is_accepted(self) -> None:
        # Arrange
        payload = {
            "start_seconds": 0.0,
            "end_seconds": 30.0,
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 1080,
            "crop_height": 1920,
            "framing_style": "solo",
        }

        # Act
        dto = VideoSegmentDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.start_seconds == 0.0
        assert dto.end_seconds == 30.0
        assert dto.framing_style == "solo"

    def test_extra_field_on_segment_is_rejected(self) -> None:
        # Arrange
        payload = {
            "start_seconds": 0.0,
            "end_seconds": 30.0,
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 1080,
            "crop_height": 1920,
            "framing_style": "solo",
            "rejected": "field",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            VideoSegmentDTO(**payload)  # type: ignore[arg-type]


class TestFfmpegEncodingPlanDTO:
    def test_valid_encoding_plan_is_accepted(self) -> None:
        # Arrange
        segment = {
            "start_seconds": 0.0,
            "end_seconds": 30.0,
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 1080,
            "crop_height": 1920,
            "framing_style": "solo",
        }
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "ffmpeg_engineer",
            "generated_at": "2026-03-16T10:00:00Z",
            "segments": [segment],
        }

        # Act
        dto = FfmpegEncodingPlanDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert len(dto.segments) == 1
        assert dto.codec == "libx264"
        assert dto.bitrate == "4M"
        assert dto.thread_count == 2
        assert dto.output_resolution == "1080x1920"

    def test_custom_codec_overrides_default(self) -> None:
        # Arrange
        segment = {
            "start_seconds": 0.0,
            "end_seconds": 30.0,
            "crop_x": 0,
            "crop_y": 0,
            "crop_width": 1080,
            "crop_height": 1920,
            "framing_style": "solo",
        }
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "ffmpeg_engineer",
            "generated_at": "2026-03-16T10:00:00Z",
            "segments": [segment],
            "codec": "libx265",
            "bitrate": "6M",
            "thread_count": 4,
            "output_resolution": "720x1280",
        }

        # Act
        dto = FfmpegEncodingPlanDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.codec == "libx265"
        assert dto.bitrate == "6M"
        assert dto.thread_count == 4
        assert dto.output_resolution == "720x1280"

    def test_extra_field_on_encoding_plan_is_rejected(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "ffmpeg_engineer",
            "generated_at": "2026-03-16T10:00:00Z",
            "segments": [],
            "forbidden": "value",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            FfmpegEncodingPlanDTO(**payload)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# AssemblyReportDTO
# ---------------------------------------------------------------------------


class TestAssemblyReportDTO:
    def test_valid_assembly_report_is_accepted(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "assembly",
            "generated_at": "2026-03-16T10:00:00Z",
            "final_reel_path": "/workspace/runs/run-001/final-reel.mp4",
            "total_duration_seconds": 58.5,
            "segment_count": 3,
            "quality_score": 0.92,
        }

        # Act
        dto = AssemblyReportDTO(**payload)  # type: ignore[arg-type]

        # Assert
        assert dto.final_reel_path == "/workspace/runs/run-001/final-reel.mp4"
        assert dto.total_duration_seconds == 58.5
        assert dto.segment_count == 3
        assert dto.quality_score == 0.92

    def test_extra_field_on_assembly_report_is_rejected(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "assembly",
            "generated_at": "2026-03-16T10:00:00Z",
            "final_reel_path": "/workspace/final-reel.mp4",
            "total_duration_seconds": 58.5,
            "segment_count": 3,
            "quality_score": 0.92,
            "forbidden": "rejected",
        }

        # Act & Assert
        with pytest.raises(ValidationError):
            AssemblyReportDTO(**payload)  # type: ignore[arg-type]

    def test_missing_final_reel_path_raises_validation_error(self) -> None:
        # Arrange
        payload = {
            "pipeline_run_id": "run-2026-abc",
            "stage_name": "assembly",
            "generated_at": "2026-03-16T10:00:00Z",
            "total_duration_seconds": 58.5,
            "segment_count": 3,
            "quality_score": 0.92,
        }

        # Act & Assert
        with pytest.raises(ValidationError) as excinfo:
            AssemblyReportDTO(**payload)  # type: ignore[arg-type]
        assert "final_reel_path" in str(excinfo.value)
