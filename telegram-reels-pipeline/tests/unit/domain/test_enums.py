"""Tests for domain enums — member coverage and stage ordering."""

from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus, RevisionType


class TestPipelineStage:
    def test_has_all_expected_members(self) -> None:
        expected = {
            "ROUTER",
            "RESEARCH",
            "TRANSCRIPT",
            "CONTENT",
            "LAYOUT_DETECTIVE",
            "FFMPEG_ENGINEER",
            "ASSEMBLY",
            "DELIVERY",
            "COMPLETED",
            "FAILED",
        }
        actual = {member.name for member in PipelineStage}
        assert actual == expected

    def test_member_count(self) -> None:
        assert len(PipelineStage) == 10

    def test_values_are_snake_case(self) -> None:
        for member in PipelineStage:
            assert member.value == member.value.lower(), f"{member.name} value should be lowercase"
            assert " " not in member.value, f"{member.name} value should not contain spaces"


class TestQADecision:
    def test_has_all_expected_members(self) -> None:
        expected = {"PASS", "REWORK", "FAIL"}
        actual = {member.name for member in QADecision}
        assert actual == expected

    def test_values_are_uppercase(self) -> None:
        for member in QADecision:
            assert member.value == member.value.upper()


class TestQAStatus:
    def test_has_all_expected_members(self) -> None:
        expected = {"PENDING", "PASSED", "REWORK", "FAILED"}
        actual = {member.name for member in QAStatus}
        assert actual == expected

    def test_member_count(self) -> None:
        assert len(QAStatus) == 4

    def test_values_are_lowercase(self) -> None:
        for member in QAStatus:
            assert member.value == member.value.lower()


class TestEscalationState:
    def test_has_all_expected_members(self) -> None:
        expected = {"NONE", "LAYOUT_UNKNOWN", "QA_EXHAUSTED", "ERROR_ESCALATED"}
        actual = {member.name for member in EscalationState}
        assert actual == expected

    def test_member_count(self) -> None:
        assert len(EscalationState) == 4


class TestRevisionType:
    def test_has_all_expected_members(self) -> None:
        expected = {"EXTEND_MOMENT", "FIX_FRAMING", "DIFFERENT_MOMENT", "ADD_CONTEXT"}
        actual = {member.name for member in RevisionType}
        assert actual == expected

    def test_member_count(self) -> None:
        assert len(RevisionType) == 4

    def test_values_are_snake_case(self) -> None:
        for member in RevisionType:
            assert member.value == member.value.lower()
