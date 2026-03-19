"""Unit tests for ResumePointDetectorService — detect_resume_point pure function."""

from __future__ import annotations

from pipeline.application.services.resume_point_detector_service import detect_resume_point
from pipeline.domain.event_types import PipelineStateEvent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(event_name: str, stage_name: str = "") -> PipelineStateEvent:
    """Build a PipelineStateEvent for testing."""
    return PipelineStateEvent(
        event_name=event_name,
        stage_name=stage_name,
        occurred_at="2026-03-10T10:00:00Z",
    )


def _stage_completed_event(stage_name: str) -> PipelineStateEvent:
    """Build a stage_completed event for a specific stage."""
    return _make_event("stage_completed", stage_name=stage_name)


# ---------------------------------------------------------------------------
# detect_resume_point tests — no events
# ---------------------------------------------------------------------------


class TestDetectResumePointNoEvents:
    def test_returns_router_when_no_events(self) -> None:
        # Arrange
        events: tuple[PipelineStateEvent, ...] = ()

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "router"

    def test_returns_router_when_only_non_stage_completed_events(self) -> None:
        # Arrange
        events = (
            _make_event("pipeline_started"),
            _make_event("pipeline_paused"),
        )

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "router"


# ---------------------------------------------------------------------------
# detect_resume_point tests — single stage completed
# ---------------------------------------------------------------------------


class TestDetectResumePointSingleCompleted:
    def test_returns_next_stage_after_router(self) -> None:
        # Arrange
        events = (_stage_completed_event("router"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "research"

    def test_returns_next_stage_after_research(self) -> None:
        # Arrange
        events = (_stage_completed_event("research"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "transcript"

    def test_returns_next_stage_after_transcript(self) -> None:
        # Arrange
        events = (_stage_completed_event("transcript"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "content"

    def test_returns_next_stage_after_content(self) -> None:
        # Arrange
        events = (_stage_completed_event("content"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "layout_detective"

    def test_returns_next_stage_after_layout_detective(self) -> None:
        # Arrange
        events = (_stage_completed_event("layout_detective"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "ffmpeg_engineer"

    def test_returns_next_stage_after_ffmpeg_engineer(self) -> None:
        # Arrange
        events = (_stage_completed_event("ffmpeg_engineer"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "veo3_await"

    def test_returns_next_stage_after_assembly(self) -> None:
        # Arrange
        events = (_stage_completed_event("assembly"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "delivery"


# ---------------------------------------------------------------------------
# detect_resume_point tests — multiple events, finds last completed
# ---------------------------------------------------------------------------


class TestDetectResumePointMultipleEvents:
    def test_uses_last_stage_completed_event(self) -> None:
        # Arrange
        events = (
            _make_event("pipeline_started"),
            _stage_completed_event("router"),
            _make_event("pipeline_paused"),
            _stage_completed_event("research"),
            _make_event("pipeline_paused"),
        )

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "transcript"

    def test_ignores_events_after_last_stage_completed(self) -> None:
        # Arrange
        events = (
            _stage_completed_event("router"),
            _stage_completed_event("research"),
            _stage_completed_event("transcript"),
            _make_event("pipeline_paused"),
            _make_event("pipeline_resumed"),
        )

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "content"

    def test_mixed_event_types_finds_correct_resume_point(self) -> None:
        # Arrange
        events = (
            _make_event("pipeline_started"),
            _stage_completed_event("router"),
            _make_event("stage_started", stage_name="research"),
            _stage_completed_event("research"),
            _make_event("stage_started", stage_name="transcript"),
            _make_event("pipeline_paused"),
        )

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "transcript"


# ---------------------------------------------------------------------------
# detect_resume_point tests — edge cases
# ---------------------------------------------------------------------------


class TestDetectResumePointEdgeCases:
    def test_returns_router_for_unknown_stage_name(self) -> None:
        # Arrange
        events = (_stage_completed_event("bogus_stage_name"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "router"

    def test_stage_completed_event_with_empty_stage_name_is_ignored(self) -> None:
        # Arrange
        events = (
            PipelineStateEvent(event_name="stage_completed", stage_name=""),
            _stage_completed_event("router"),
        )

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "research"

    def test_single_stage_completed_event_returns_correct_next(self) -> None:
        # Arrange
        events = (_stage_completed_event("layout_detective"),)

        # Act
        resume_stage = detect_resume_point(events)

        # Assert
        assert resume_stage == "ffmpeg_engineer"
