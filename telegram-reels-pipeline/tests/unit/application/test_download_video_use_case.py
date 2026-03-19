"""Unit tests for DownloadVideoUseCase — event emission behaviour."""

from __future__ import annotations

from pipeline.application.services.pipeline_event_emitter_service import (
    PipelineEventEmitterService,
)
from pipeline.application.use_cases.download_video_use_case import (
    DOWNLOAD_STAGE_NAME,
    DownloadVideoUseCase,
)
from pipeline.domain.event_types import STAGE_COMPLETED, STAGE_ENTERED
from tests.fakes.fake_event_store import FakeEventStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PIPELINE_RUN_ID = "run-2026-03-18-abc123"
_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def _make_use_case() -> tuple[DownloadVideoUseCase, FakeEventStore]:
    """Build a DownloadVideoUseCase wired to a FakeEventStore."""
    fake_event_store = FakeEventStore()
    emitter_service = PipelineEventEmitterService(event_store=fake_event_store)
    use_case = DownloadVideoUseCase(event_emitter=emitter_service)
    return use_case, fake_event_store


# ---------------------------------------------------------------------------
# Test: execute emits two events in order
# ---------------------------------------------------------------------------


class TestDownloadVideoUseCaseEmitsEvents:
    async def test_execute_emits_stage_entered_and_stage_completed(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        assert len(fake_event_store.appended_events) == 2
        assert fake_event_store.appended_events[0].event_type == STAGE_ENTERED
        assert fake_event_store.appended_events[1].event_type == STAGE_COMPLETED

    async def test_stage_entered_is_emitted_before_stage_completed(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        event_types = [e.event_type for e in fake_event_store.appended_events]
        assert event_types.index(STAGE_ENTERED) < event_types.index(STAGE_COMPLETED)

    async def test_events_carry_correct_pipeline_run_id(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        for emitted_event in fake_event_store.appended_events:
            assert emitted_event.pipeline_run_id == _PIPELINE_RUN_ID

    async def test_events_carry_research_stage_name(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        for emitted_event in fake_event_store.appended_events:
            assert emitted_event.stage_name == DOWNLOAD_STAGE_NAME
            assert emitted_event.stage_name == "research"


# ---------------------------------------------------------------------------
# Test: stage_completed event payload contains artifact keys
# ---------------------------------------------------------------------------


class TestDownloadVideoUseCaseCompletedPayload:
    async def test_completed_event_payload_contains_youtube_url(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        completed_event = fake_event_store.appended_events[1]
        assert completed_event.payload.get("youtube_url") == _YOUTUBE_URL

    async def test_completed_event_payload_contains_video_file_path_key(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        completed_event = fake_event_store.appended_events[1]
        assert "video_file_path" in completed_event.payload

    async def test_stage_entered_event_payload_is_empty(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        entered_event = fake_event_store.appended_events[0]
        assert len(entered_event.payload) == 0


# ---------------------------------------------------------------------------
# Test: events have a non-empty timestamp
# ---------------------------------------------------------------------------


class TestDownloadVideoUseCaseTimestamp:
    async def test_all_events_have_non_empty_timestamp(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute(_PIPELINE_RUN_ID, _YOUTUBE_URL)

        # Assert
        for emitted_event in fake_event_store.appended_events:
            assert emitted_event.timestamp != ""


# ---------------------------------------------------------------------------
# Test: multiple executions emit independent event sets
# ---------------------------------------------------------------------------


class TestDownloadVideoUseCaseIsolation:
    async def test_two_executions_emit_four_events_total(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute("run-001", _YOUTUBE_URL)
        await use_case.execute("run-002", _YOUTUBE_URL)

        # Assert
        assert len(fake_event_store.appended_events) == 4

    async def test_load_events_filters_by_run_id(self) -> None:
        # Arrange
        use_case, fake_event_store = _make_use_case()

        # Act
        await use_case.execute("run-001", _YOUTUBE_URL)
        await use_case.execute("run-002", _YOUTUBE_URL)
        run_001_events = await fake_event_store.load_events("run-001")

        # Assert
        assert len(run_001_events) == 2
        for emitted_event in run_001_events:
            assert emitted_event.pipeline_run_id == "run-001"
