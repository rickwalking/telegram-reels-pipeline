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
        """Record the event in memory."""
        self.events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> list[PipelineStateEvent]:
        """Filter events by run id."""
        return [e for e in self.events if e.pipeline_run_id == pipeline_run_id]


class FakeProjectionStore:
    """In-memory fake implementing ProjectionStorePort for unit tests."""

    def __init__(self) -> None:
        self.projections: dict[str, RunStateProjection] = {}

    async def save_projection(self, projection: RunStateProjection) -> None:
        """Store projection keyed by run id."""
        self.projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        """Look up projection by run id."""
        return self.projections.get(pipeline_run_id)


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    """Provide a fresh in-memory event store."""
    return FakeEventStore()


@pytest.fixture()
def fake_projection_store() -> FakeProjectionStore:
    """Provide a fresh in-memory projection store."""
    return FakeProjectionStore()


async def test_trigger_creates_event_and_projection(
    fake_event_store: FakeEventStore,
    fake_projection_store: FakeProjectionStore,
) -> None:
    """Happy path: executing the use case persists both an event and a projection."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = CreatePipelineRunCommand(
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        topic_focus="AI breakthroughs",
        trigger_source="api",
    )
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_projection_store)

    # Act
    projection = await use_case.execute(command)

    # Assert
    assert projection.pipeline_run_id != ""
    assert projection.youtube_url == command.youtube_url
    assert projection.trigger_source == "api"
    assert projection.execution_status == RunExecutionStatus.PENDING.value
    assert projection.current_stage == "router"
    assert projection.escalation_status == EscalationState.NONE.value
    assert projection.qa_evaluation_status == QAStatus.PENDING.value


async def test_trigger_appends_exactly_one_event(
    fake_event_store: FakeEventStore,
    fake_projection_store: FakeProjectionStore,
) -> None:
    """The use case should append exactly one creation event to the event store."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = CreatePipelineRunCommand(
        youtube_url="https://www.youtube.com/watch?v=abc12345678",
        topic_focus="",
        trigger_source="telegram",
    )
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_projection_store)

    # Act
    await use_case.execute(command)

    # Assert
    assert len(fake_event_store.events) == 1
    event = fake_event_store.events[0]
    assert event.event_type == "pipeline_run_created"
    assert event.payload_data["youtube_url"] == command.youtube_url


async def test_trigger_saves_projection_to_store(
    fake_event_store: FakeEventStore,
    fake_projection_store: FakeProjectionStore,
) -> None:
    """The use case should persist the projection so it can be loaded later."""
    # Arrange
    from pipeline.application.use_cases.trigger_pipeline_run_use_case import TriggerPipelineRunUseCase

    command = CreatePipelineRunCommand(
        youtube_url="https://www.youtube.com/watch?v=xyz98765432",
        topic_focus="testing topic",
        trigger_source="cli",
    )
    use_case = TriggerPipelineRunUseCase(fake_event_store, fake_projection_store)

    # Act
    result = await use_case.execute(command)

    # Assert
    loaded = await fake_projection_store.load_projection(result.pipeline_run_id)
    assert loaded is not None
    assert loaded.pipeline_run_id == result.pipeline_run_id
    assert loaded.trigger_source == "cli"
