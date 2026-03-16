"""Unit tests for TriggerPipelineRunUseCase — happy path with faked ports."""

from __future__ import annotations

import pytest

from pipeline.domain.enums import EscalationState, QAStatus, RunExecutionStatus
from pipeline.domain.events import CreatePipelineRunCommand, PipelineStateEvent, RunStateProjection


class FakeEventStore:
    """In-memory fake implementing EventStorePort for unit tests."""

    def __init__(self) -> None:
        self.events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        self.events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        return tuple(e for e in self.events if e.pipeline_run_id == pipeline_run_id)

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        return len([e for e in self.events if e.pipeline_run_id == pipeline_run_id])


class FakeStateStore:
    """In-memory fake implementing StateStorePort for unit tests."""

    def __init__(self) -> None:
        self.projections: dict[str, RunStateProjection] = {}

    async def save_state(self, projection: RunStateProjection) -> None:
        self.projections[projection.pipeline_run_id] = projection

    async def load_state(self, pipeline_run_id: str) -> RunStateProjection | None:
        return self.projections.get(pipeline_run_id)

    async def list_incomplete_runs(self) -> list[RunStateProjection]:
        return [p for p in self.projections.values() if p.execution_status != RunExecutionStatus.COMPLETED.value]


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    return FakeEventStore()


@pytest.fixture()
def fake_state_store() -> FakeStateStore:
    return FakeStateStore()


def _make_command(
    youtube_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    topic_focus: str = "AI breakthroughs",
    trigger_source: str = "api_client",
) -> CreatePipelineRunCommand:
    return CreatePipelineRunCommand(
        youtube_url=youtube_url,
        topic_focus=topic_focus,
        trigger_source=trigger_source,
        client_identifier="test-client",
    )


async def test_trigger_creates_event_and_projection(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """Happy path: executing the use case persists both an event and a projection."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = _make_command()
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    projection = await use_case.execute(command)

    # Assert
    assert projection.pipeline_run_id != ""
    assert projection.youtube_url == command.youtube_url
    assert projection.trigger_source == "api_client"
    assert projection.execution_status == RunExecutionStatus.PENDING.value
    assert projection.current_stage == "router"
    assert projection.escalation_status == EscalationState.NONE.value
    assert projection.qa_evaluation_status == QAStatus.PENDING.value


async def test_trigger_appends_exactly_one_event(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should append exactly one creation event to the event store."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = _make_command(trigger_source="telegram_bot")
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    await use_case.execute(command)

    # Assert
    assert len(fake_event_store.events) == 1
    event = fake_event_store.events[0]
    assert "pipeline" in event.event_type and "created" in event.event_type
    assert event.payload_data["youtube_url"] == command.youtube_url


async def test_trigger_saves_projection_to_store(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should persist the projection so it can be loaded later."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = _make_command(trigger_source="cli")
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    result = await use_case.execute(command)

    # Assert
    loaded = await fake_state_store.load_state(result.pipeline_run_id)
    assert loaded is not None
    assert loaded.pipeline_run_id == result.pipeline_run_id
    assert loaded.trigger_source == "cli"
