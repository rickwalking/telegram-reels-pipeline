"""BDD step definitions for Queue Pipeline Runs feature."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase
from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase
from pipeline.domain.events import CreatePipelineRunCommand, PipelineStateEvent, RunStateProjection

# ---------------------------------------------------------------------------
# In-memory fake adapters
# ---------------------------------------------------------------------------


class FakeEventStore:
    """In-memory event store for BDD testing."""

    def __init__(self) -> None:
        self.events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        """Append event to in-memory list."""
        self.events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        """Return events filtered by pipeline_run_id."""
        return tuple(e for e in self.events if e.pipeline_run_id == pipeline_run_id)

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        """Return event count for a specific run."""
        return len([e for e in self.events if e.pipeline_run_id == pipeline_run_id])


class FakeStateStore:
    """In-memory projection store for BDD testing."""

    def __init__(self) -> None:
        self.projections: dict[str, RunStateProjection] = {}

    async def save_state(self, projection: RunStateProjection) -> None:
        """Save projection to in-memory dictionary."""
        self.projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Load projection by pipeline_run_id."""
        return self.projections.get(pipeline_run_id)

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
        """List projections matching the given execution status."""
        return [p for p in self.projections.values() if p.execution_status == execution_status]

    async def list_all_projections(self) -> list[RunStateProjection]:
        """List all projections."""
        return list(self.projections.values())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coroutine: Any) -> Any:
    """Execute a coroutine synchronously by creating a new event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    """Provide a fresh in-memory event store."""
    return FakeEventStore()


@pytest.fixture()
def fake_state_store() -> FakeStateStore:
    """Provide a fresh in-memory state store."""
    return FakeStateStore()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@scenario(
    "../features/queue_pipeline_runs.feature",
    "First run starts immediately when no other runs are active",
)
def test_first_run_starts_immediately() -> None:
    """Scenario: first run claimed immediately."""


@scenario(
    "../features/queue_pipeline_runs.feature",
    "Second run queues while first is active",
)
def test_second_run_queues_while_first_active() -> None:
    """Scenario: second run stays pending."""


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


@given("no pipeline runs exist in the system")
def given_no_runs_exist(fake_state_store: FakeStateStore) -> None:
    """Ensure the state store is empty."""
    assert len(fake_state_store.projections) == 0


@given(
    parsers.parse('a pipeline run with URL "{youtube_url}" is "{execution_status}"'),
    target_fixture="existing_run_projection",
)
def given_existing_run(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
    youtube_url: str,
    execution_status: str,
) -> RunStateProjection:
    """Create a run in the given execution status."""
    command = CreatePipelineRunCommand(
        youtube_url=youtube_url,
        trigger_source="api_client",
    )
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_state_store)
    projection = _run_async(use_case.execute(command))

    updated_projection = RunStateProjection(
        pipeline_run_id=projection.pipeline_run_id,
        youtube_url=projection.youtube_url,
        trigger_source=projection.trigger_source,
        current_stage=projection.current_stage,
        execution_status=execution_status,
        current_attempt_count=projection.current_attempt_count,
        qa_evaluation_status=projection.qa_evaluation_status,
        completed_stages=projection.completed_stages,
        escalation_status=projection.escalation_status,
        created_at=projection.created_at,
        last_updated_at=projection.last_updated_at,
    )
    _run_async(fake_state_store.save_state(updated_projection))
    return updated_projection


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------


@when(
    parsers.parse('I trigger a new pipeline run with URL "{youtube_url}"'),
    target_fixture="triggered_projection",
)
def when_trigger_new_run(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
    youtube_url: str,
) -> RunStateProjection:
    """Trigger a new pipeline run via the use case."""
    command = CreatePipelineRunCommand(
        youtube_url=youtube_url,
        trigger_source="api_client",
    )
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_state_store)
    return _run_async(use_case.execute(command))


@when(
    "the orchestrator claims the next pending run",
    target_fixture="claimed_projection",
)
def when_orchestrator_claims(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> RunStateProjection | None:
    """Execute the claim use case to pick up the next pending run."""
    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)
    return _run_async(use_case.execute())


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


@then(parsers.parse('the claimed run execution_status should be "{expected_status}"'))
def then_claimed_run_status(claimed_projection: RunStateProjection, expected_status: str) -> None:
    """Assert the claimed run has the expected execution status."""
    assert claimed_projection is not None
    assert claimed_projection.execution_status == expected_status


@then(parsers.parse("exactly {count:d} event should be emitted for the claimed run"))
def then_event_count_for_claimed_run(
    fake_event_store: FakeEventStore,
    claimed_projection: RunStateProjection,
    count: int,
) -> None:
    """Assert the correct number of claim events were emitted for the run."""
    run_events = [
        e
        for e in fake_event_store.events
        if e.pipeline_run_id == claimed_projection.pipeline_run_id and "claimed" in e.event_type
    ]
    assert len(run_events) == count


@then(parsers.parse('the new run execution_status should be "{expected_status}"'))
def then_new_run_status(triggered_projection: RunStateProjection, expected_status: str) -> None:
    """Assert the newly triggered run has the expected execution status."""
    assert triggered_projection.execution_status == expected_status


@then(parsers.parse("the system should have {count:d} total pipeline runs"))
def then_total_run_count(fake_state_store: FakeStateStore, count: int) -> None:
    """Assert the total number of pipeline runs in the state store."""
    assert len(fake_state_store.projections) == count
