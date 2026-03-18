"""Tests for the InMemoryPipelineEventStore adapter."""

from __future__ import annotations

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent
from pipeline.domain.types import EventId, RunId
from pipeline.infrastructure.adapters.in_memory_event_store import InMemoryPipelineEventStore

RUN_ID = RunId("run-test-001")


def _make_event(name: str) -> PipelineEvent:
    """Helper to build a PipelineEvent."""
    return PipelineEvent(
        timestamp="2026-03-18T10:00:00Z",
        event_name=name,
        stage=PipelineStage.ROUTER,
    )


class TestAppendAndListEvents:
    """Tests for append_event and list_events_for_run."""

    async def test_append_returns_stored_event_with_id(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()

        # Act
        stored = await store.append_event(RUN_ID, _make_event("test.event"))

        # Assert
        assert stored.event_id.startswith("evt-")
        assert stored.pipeline_run_id == RUN_ID
        assert stored.event.event_name == "test.event"

    async def test_list_returns_events_in_order(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        await store.append_event(RUN_ID, _make_event("first"))
        await store.append_event(RUN_ID, _make_event("second"))
        await store.append_event(RUN_ID, _make_event("third"))

        # Act
        events, total = await store.list_events_for_run(RUN_ID)

        # Assert
        assert total == 3
        assert len(events) == 3
        assert events[0].event.event_name == "first"
        assert events[2].event.event_name == "third"

    async def test_list_respects_pagination(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        for i in range(10):
            await store.append_event(RUN_ID, _make_event(f"event-{i}"))

        # Act
        events, total = await store.list_events_for_run(RUN_ID, offset=3, limit=4)

        # Assert
        assert total == 10
        assert len(events) == 4
        assert events[0].event.event_name == "event-3"
        assert events[3].event.event_name == "event-6"

    async def test_empty_run_returns_zero(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()

        # Act
        events, total = await store.list_events_for_run(RunId("nonexistent"))

        # Assert
        assert total == 0
        assert events == ()


class TestGetEventById:
    """Tests for get_event_by_id."""

    async def test_found(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        stored = await store.append_event(RUN_ID, _make_event("target"))

        # Act
        result = await store.get_event_by_id(RUN_ID, stored.event_id)

        # Assert
        assert result is not None
        assert result.event_id == stored.event_id

    async def test_not_found(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()

        # Act
        result = await store.get_event_by_id(RUN_ID, EventId("evt-missing"))

        # Assert
        assert result is None

    async def test_wrong_run_returns_none(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        stored = await store.append_event(RUN_ID, _make_event("event"))

        # Act
        result = await store.get_event_by_id(RunId("other-run"), stored.event_id)

        # Assert
        assert result is None


class TestEventBusListenerMode:
    """Tests for __call__ (EventBus listener) behavior."""

    async def test_call_stores_event_under_current_run(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        store.set_current_run_id(RUN_ID)

        # Act
        await store(_make_event("bus.event"))

        # Assert
        events, total = await store.list_events_for_run(RUN_ID)
        assert total == 1
        assert events[0].event.event_name == "bus.event"

    async def test_call_without_current_run_id_is_ignored(self) -> None:
        # Arrange
        store = InMemoryPipelineEventStore()
        # No set_current_run_id call

        # Act
        await store(_make_event("orphan.event"))

        # Assert
        events, total = await store.list_events_for_run(RunId(""))
        assert total == 0
