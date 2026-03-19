"""Unit tests for SaveStageOutputUseCase — event creation and projection update."""

from __future__ import annotations

import pytest

from pipeline.application.use_cases.save_stage_output_use_case import (
    SaveStageOutputCommand,
    SaveStageOutputUseCase,
)
from pipeline.domain.event_types import STAGE_OUTPUT_SAVED
from pipeline.domain.events import RunStateProjection
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


def _make_pending_projection(
    pipeline_run_id: str = "20260316-120000-abc12345",
    youtube_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
) -> RunStateProjection:
    """Build a minimal RunStateProjection for testing."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url=youtube_url,
        trigger_source="api_client",
        current_stage="router",
        execution_status="in_progress",
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=(),
        escalation_status="none",
        created_at="2026-03-16T12:00:00+00:00",
        last_updated_at="2026-03-16T12:00:00+00:00",
    )


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    """Provide a fresh FakeEventStore for each test."""
    return FakeEventStore()


@pytest.fixture()
def fake_state_store() -> FakeStateStore:
    """Provide a fresh FakeStateStore for each test."""
    return FakeStateStore()


@pytest.fixture()
def use_case(fake_event_store: FakeEventStore, fake_state_store: FakeStateStore) -> SaveStageOutputUseCase:
    """Provide a SaveStageOutputUseCase wired with fake ports."""
    return SaveStageOutputUseCase(fake_event_store, fake_state_store)


async def test_saves_event_with_stage_output_saved_type(
    use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should append a STAGE_OUTPUT_SAVED event to the event store."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-001")
    await fake_state_store.save_state(projection)
    command = SaveStageOutputCommand(
        pipeline_run_id="run-001",
        stage_name="router",
        payload_data={"tier": "short", "topic_focus": "AI"},
    )

    # Act
    await use_case.execute(command)

    # Assert
    events = await fake_event_store.get_events_for_run("run-001")
    assert len(events) == 1
    saved_event = events[0]
    assert saved_event.event_type == STAGE_OUTPUT_SAVED
    assert saved_event.stage_name == "router"
    assert saved_event.pipeline_run_id == "run-001"


async def test_event_payload_contains_provided_data(
    use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The event payload must reflect the data from the SaveStageOutputCommand."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-002")
    await fake_state_store.save_state(projection)
    command = SaveStageOutputCommand(
        pipeline_run_id="run-002",
        stage_name="research",
        payload_data={"episode_title": "AI Podcast", "context_summary": "Great episode"},
    )

    # Act
    await use_case.execute(command)

    # Assert
    events = await fake_event_store.get_events_for_run("run-002")
    assert events[0].payload_data["episode_title"] == "AI Podcast"
    assert events[0].payload_data["context_summary"] == "Great episode"


async def test_returns_event_id_string(
    use_case: SaveStageOutputUseCase,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should return the event_id of the persisted event."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-003")
    await fake_state_store.save_state(projection)
    command = SaveStageOutputCommand(
        pipeline_run_id="run-003",
        stage_name="router",
        payload_data={"tier": "short"},
    )

    # Act
    event_id = await use_case.execute(command)

    # Assert
    assert isinstance(event_id, str)
    assert event_id.startswith("evt-")


async def test_updates_projection_completed_stages(
    use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The projection's completed_stages should include the saved stage after execution."""
    # Arrange
    projection = _make_pending_projection(pipeline_run_id="run-004")
    await fake_state_store.save_state(projection)
    command = SaveStageOutputCommand(
        pipeline_run_id="run-004",
        stage_name="transcript",
        payload_data={"moments": []},
    )

    # Act
    await use_case.execute(command)

    # Assert
    updated_projection = await fake_state_store.load_projection("run-004")
    assert updated_projection is not None
    assert "transcript" in updated_projection.completed_stages


async def test_does_not_duplicate_stage_in_completed_stages(
    use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """Saving a stage twice should not duplicate it in completed_stages."""
    # Arrange
    projection = RunStateProjection(
        pipeline_run_id="run-005",
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        trigger_source="api_client",
        current_stage="router",
        execution_status="in_progress",
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=("router",),
        escalation_status="none",
        created_at="2026-03-16T12:00:00+00:00",
        last_updated_at="2026-03-16T12:00:00+00:00",
    )
    await fake_state_store.save_state(projection)
    command = SaveStageOutputCommand(
        pipeline_run_id="run-005",
        stage_name="router",
        payload_data={"tier": "short"},
    )

    # Act
    await use_case.execute(command)

    # Assert
    updated = await fake_state_store.load_projection("run-005")
    assert updated is not None
    assert updated.completed_stages.count("router") == 1


async def test_does_not_crash_when_no_projection_exists(
    use_case: SaveStageOutputUseCase,
    fake_event_store: FakeEventStore,
) -> None:
    """If no projection exists for the run, the event should still be saved without error."""
    # Arrange
    command = SaveStageOutputCommand(
        pipeline_run_id="run-no-projection",
        stage_name="router",
        payload_data={"tier": "short"},
    )

    # Act
    event_id = await use_case.execute(command)

    # Assert
    events = await fake_event_store.get_events_for_run("run-no-projection")
    assert len(events) == 1
    assert event_id.startswith("evt-")
