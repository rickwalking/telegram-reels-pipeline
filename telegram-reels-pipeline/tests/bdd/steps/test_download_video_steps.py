"""BDD step definitions for the download_video.feature scenario."""

from __future__ import annotations

import pytest
from pytest_bdd import given, scenario, then, when

from pipeline.application.services.pipeline_event_emitter_service import (
    PipelineEventEmitterService,
)
from pipeline.application.use_cases.download_video_use_case import DownloadVideoUseCase
from pipeline.domain.event_types import STAGE_COMPLETED, STAGE_ENTERED
from tests.fakes.fake_event_store import FakeEventStore

# ---------------------------------------------------------------------------
# Scenario binding
# ---------------------------------------------------------------------------

FEATURE_FILE = "download_video.feature"


@scenario(f"../features/{FEATURE_FILE}", "Successfully download video emits events")
def test_successfully_download_video_emits_events() -> None:
    """Bind the BDD scenario to a pytest test function."""


# ---------------------------------------------------------------------------
# Shared state container
# ---------------------------------------------------------------------------


@pytest.fixture
def bdd_context() -> dict[str, object]:
    """Mutable context dictionary shared across step functions."""
    return {}


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given('a pipeline run with id "run-bdd-2026-03-18"', target_fixture="bdd_context")
def given_pipeline_run_id() -> dict[str, object]:
    """Initialise context with the pipeline run identifier."""
    return {"pipeline_run_id": "run-bdd-2026-03-18"}


@given(
    'a YouTube URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"',
    target_fixture="bdd_context",
)
def given_youtube_url(bdd_context: dict[str, object]) -> dict[str, object]:
    """Add the YouTube URL to the shared context."""
    bdd_context["youtube_url"] = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    return bdd_context


# ---------------------------------------------------------------------------
# When step
# ---------------------------------------------------------------------------


@when("the download video use case executes", target_fixture="bdd_context")
def when_use_case_executes(bdd_context: dict[str, object]) -> dict[str, object]:
    """Execute the use case and capture the fake event store."""
    import asyncio

    fake_event_store = FakeEventStore()
    emitter_service = PipelineEventEmitterService(event_store=fake_event_store)
    use_case = DownloadVideoUseCase(event_emitter=emitter_service)

    pipeline_run_id = str(bdd_context["pipeline_run_id"])
    youtube_url = str(bdd_context["youtube_url"])

    asyncio.run(use_case.execute(pipeline_run_id, youtube_url))

    bdd_context["fake_event_store"] = fake_event_store
    return bdd_context


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then('a "pipeline.stage_entered" event is emitted for stage "research"')
def then_stage_entered_emitted(bdd_context: dict[str, object]) -> None:
    """Assert a stage_entered event exists for the research stage."""
    fake_event_store = bdd_context["fake_event_store"]
    assert isinstance(fake_event_store, FakeEventStore)
    entered_events = [
        event
        for event in fake_event_store.appended_events
        if event.event_type == STAGE_ENTERED and event.stage_name == "research"
    ]
    assert len(entered_events) == 1


@then('a "pipeline.stage_completed" event is emitted for stage "research"')
def then_stage_completed_emitted(bdd_context: dict[str, object]) -> None:
    """Assert a stage_completed event exists for the research stage."""
    fake_event_store = bdd_context["fake_event_store"]
    assert isinstance(fake_event_store, FakeEventStore)
    completed_events = [
        event
        for event in fake_event_store.appended_events
        if event.event_type == STAGE_COMPLETED and event.stage_name == "research"
    ]
    assert len(completed_events) == 1


@then('all events carry the pipeline run id "run-bdd-2026-03-18"')
def then_all_events_carry_run_id(bdd_context: dict[str, object]) -> None:
    """Assert every emitted event has the correct pipeline run id."""
    fake_event_store = bdd_context["fake_event_store"]
    assert isinstance(fake_event_store, FakeEventStore)
    for emitted_event in fake_event_store.appended_events:
        assert emitted_event.pipeline_run_id == "run-bdd-2026-03-18"
