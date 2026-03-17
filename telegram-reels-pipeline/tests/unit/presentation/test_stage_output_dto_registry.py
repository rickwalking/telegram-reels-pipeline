"""Unit tests for stage_output_dto_registry — stage name to DTO class dispatch."""

from __future__ import annotations

import pytest

from pipeline.presentation.dtos.assembly_report_dto import AssemblyReportDTO
from pipeline.presentation.dtos.content_output_dto import ContentOutputDTO
from pipeline.presentation.dtos.ffmpeg_encoding_plan_dto import FfmpegEncodingPlanDTO
from pipeline.presentation.dtos.layout_analysis_output_dto import LayoutAnalysisOutputDTO
from pipeline.presentation.dtos.research_output_dto import ResearchOutputDTO
from pipeline.presentation.dtos.router_output_dto import RouterOutputDTO
from pipeline.presentation.dtos.stage_output_dto_registry import (
    STAGE_OUTPUT_DTO_REGISTRY,
    get_dto_class_for_stage,
)
from pipeline.presentation.dtos.transcript_output_dto import TranscriptOutputDTO


class TestStageOutputDtoRegistryLookup:
    def test_router_stage_resolves_to_router_output_dto(self) -> None:
        # Arrange — stage name as defined in domain ubiquitous language

        # Act
        dto_class = get_dto_class_for_stage("router")

        # Assert
        assert dto_class is RouterOutputDTO

    def test_research_stage_resolves_to_research_output_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("research")
        # Assert
        assert dto_class is ResearchOutputDTO

    def test_transcript_stage_resolves_to_transcript_output_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("transcript")
        # Assert
        assert dto_class is TranscriptOutputDTO

    def test_content_stage_resolves_to_content_output_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("content")
        # Assert
        assert dto_class is ContentOutputDTO

    def test_layout_detective_stage_resolves_to_layout_analysis_output_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("layout_detective")
        # Assert
        assert dto_class is LayoutAnalysisOutputDTO

    def test_ffmpeg_engineer_stage_resolves_to_ffmpeg_encoding_plan_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("ffmpeg_engineer")
        # Assert
        assert dto_class is FfmpegEncodingPlanDTO

    def test_assembly_stage_resolves_to_assembly_report_dto(self) -> None:
        # Arrange
        # Act
        dto_class = get_dto_class_for_stage("assembly")
        # Assert
        assert dto_class is AssemblyReportDTO

    def test_registry_covers_all_seven_known_stages(self) -> None:
        # Arrange
        expected_stages = {
            "router",
            "research",
            "transcript",
            "content",
            "layout_detective",
            "ffmpeg_engineer",
            "assembly",
        }

        # Act
        registered_stages = set(STAGE_OUTPUT_DTO_REGISTRY.keys())

        # Assert
        assert registered_stages == expected_stages


class TestStageOutputDtoRegistryErrors:
    def test_unknown_stage_raises_value_error(self) -> None:
        # Arrange
        unknown_stage_name = "nonexistent_stage"

        # Act & Assert
        with pytest.raises(ValueError, match="Unknown stage"):
            get_dto_class_for_stage(unknown_stage_name)

    def test_error_message_includes_the_unknown_stage_name(self) -> None:
        # Arrange
        unknown_stage_name = "delivery"

        # Act & Assert
        with pytest.raises(ValueError, match="delivery"):
            get_dto_class_for_stage(unknown_stage_name)

    def test_error_message_lists_valid_stage_names(self) -> None:
        # Arrange
        unknown_stage_name = "unknown"

        # Act & Assert
        with pytest.raises(ValueError, match="router"):
            get_dto_class_for_stage(unknown_stage_name)

    def test_empty_stage_name_raises_value_error(self) -> None:
        # Arrange
        empty_stage_name = ""

        # Act & Assert
        with pytest.raises(ValueError):
            get_dto_class_for_stage(empty_stage_name)
