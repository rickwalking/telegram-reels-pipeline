"""BDD step definitions for event-driven state transitions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pytest_bdd import given, parsers, scenario, then, when

from pipeline.application.services.pipeline_event_emitter_service import (
    ErrorEventPayload,
    PipelineEventEmitterService,
    StageEventPayload,
)
from pipeline.domain.events import RunStateProjection
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


@dataclass
class ScenarioContext:
    """Mutable container for BDD scenario state."""

    event_store: FakeEventStore
    state_store: FakeStateStore
    emitter: PipelineEventEmitterService
    pipeline_run_id: str = "bdd-run-001"
    stage_name: str = ""


def _run_async(coro: object) -> object:
    """Run a coroutine synchronously for BDD steps."""
    return asyncio.run(coro)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Scenario: Stage completion emits event before proceeding
# ---------------------------------------------------------------------------


@scenario("features/event_driven_transitions.feature", "Stage completion emits event before proceeding")
def test_stage_completion_emits_event() -> None:
    """Stage completion emits event before proceeding."""


@given(parsers.parse('a pipeline run in "{stage_name}" stage'), target_fixture="scenario_context")
def pipeline_run_in_stage(stage_name: str) -> ScenarioContext:
    """Set up a pipeline run in the given stage."""
    event_store = FakeEventStore()
    state_store = FakeStateStore()
    emitter = PipelineEventEmitterService(event_store=event_store, state_store=state_store)
    context = ScenarioContext(
        event_store=event_store,
        state_store=state_store,
        emitter=emitter,
        stage_name=stage_name,
    )
    # Seed projection with the current stage
    projection = RunStateProjection(
        pipeline_run_id=context.pipeline_run_id,
            youtube_url="https://youtube.com/watch?v=test",
        current_stage=stage_name,
        execution_status="running",
    )
    _run_async(state_store.save_state(projection))
    return context


@when("the stage completes successfully")
def stage_completes_successfully(scenario_context: ScenarioContext) -> None:
    """Emit a stage completed event."""
    payload = StageEventPayload(
        pipeline_run_id=scenario_context.pipeline_run_id,
        stage_name=scenario_context.stage_name,
        artifact_paths=("router-output.json",),
    )
    _run_async(scenario_context.emitter.emit_stage_completed(payload))


@then(parsers.parse('a "{event_type}" event is recorded'))
def event_is_recorded(scenario_context: ScenarioContext, event_type: str) -> None:
    """Verify the expected event type was recorded."""
    matching = [e for e in scenario_context.event_store.events if e.event_type == event_type]
    assert len(matching) == 1, f"Expected 1 '{event_type}' event, found {len(matching)}"


@then("the projection shows the next stage")
def projection_shows_next_stage(scenario_context: ScenarioContext) -> None:
    """Verify projection has stage in stages_completed."""
    projection = _run_async(scenario_context.state_store.load_projection(scenario_context.pipeline_run_id))
    assert projection is not None
    assert scenario_context.stage_name in projection.completed_stages  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Scenario: Error emits event and marks run failed
# ---------------------------------------------------------------------------


@scenario("features/event_driven_transitions.feature", "Error emits event and marks run failed")
def test_error_emits_event_and_marks_failed() -> None:
    """Error emits event and marks run failed."""


@when(parsers.parse('an error occurs with message "{error_message}"'))
def error_occurs(scenario_context: ScenarioContext, error_message: str) -> None:
    """Emit an error occurred event."""
    payload = ErrorEventPayload(
        pipeline_run_id=scenario_context.pipeline_run_id,
        stage_name=scenario_context.stage_name,
        error_message=error_message,
    )
    _run_async(scenario_context.emitter.emit_error_occurred(payload))


@then(parsers.parse('the projection execution status is "{expected_status}"'))
def projection_execution_status(scenario_context: ScenarioContext, expected_status: str) -> None:
    """Verify the projection execution status matches expected."""
    projection = _run_async(scenario_context.state_store.load_projection(scenario_context.pipeline_run_id))
    assert projection is not None
    assert projection.execution_status == expected_status  # type: ignore[union-attr]
