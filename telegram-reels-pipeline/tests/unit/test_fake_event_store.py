"""Unit tests for FakeEventStore — verifies EventStorePort contract compliance."""

from __future__ import annotations

import pytest

from pipeline.domain.events import PipelineStateEvent
from pipeline.domain.ports.event_store_port import EventStorePort
from tests.fakes.fake_event_store import FakeEventStore


def _make_event(pipeline_run_id: str, event_type: str) -> PipelineStateEvent:
    """Build a minimal PipelineStateEvent for testing."""
    return PipelineStateEvent(
        event_id=f"{pipeline_run_id}-{event_type}",
        pipeline_run_id=pipeline_run_id,
        event_type=event_type,
        created_at="2026-03-16T10:00:00Z",
    )


class TestFakeEventStoreProtocolCompliance:
    """Verify FakeEventStore satisfies the EventStorePort protocol."""

    def test_fake_event_store_implements_event_store_port(self) -> None:
        # Arrange
        fake_store = FakeEventStore()

        # Act & Assert
        assert isinstance(fake_store, EventStorePort)


class TestFakeEventStoreAppendEvent:
    """Verify append_event stores events correctly."""

    @pytest.mark.asyncio
    async def test_append_single_event_increments_count(self) -> None:
        # Arrange
        fake_store = FakeEventStore()
        event = _make_event("run-001", "pipeline.run_created")

        # Act
        await fake_store.append_event(event)

        # Assert
        assert await fake_store.get_event_count_for_run("run-001") == 1

    @pytest.mark.asyncio
    async def test_append_multiple_events_preserves_order(self) -> None:
        # Arrange
        fake_store = FakeEventStore()
        event_created = _make_event("run-001", "pipeline.run_created")
        event_entered = _make_event("run-001", "pipeline.stage_entered")

        # Act
        await fake_store.append_event(event_created)
        await fake_store.append_event(event_entered)

        # Assert
        events = await fake_store.get_events_for_run("run-001")
        assert len(events) == 2
        assert events[0].event_type == "pipeline.run_created"
        assert events[1].event_type == "pipeline.stage_entered"


class TestFakeEventStoreGetEventsForRun:
    """Verify get_events_for_run filters by pipeline_run_id."""

    @pytest.mark.asyncio
    async def test_returns_empty_tuple_for_unknown_run(self) -> None:
        # Arrange
        fake_store = FakeEventStore()

        # Act
        events = await fake_store.get_events_for_run("nonexistent-run")

        # Assert
        assert events == ()

    @pytest.mark.asyncio
    async def test_isolates_events_by_run_id(self) -> None:
        # Arrange
        fake_store = FakeEventStore()
        await fake_store.append_event(_make_event("run-001", "pipeline.run_created"))
        await fake_store.append_event(_make_event("run-002", "pipeline.run_created"))
        await fake_store.append_event(_make_event("run-001", "pipeline.stage_entered"))

        # Act
        run_001_events = await fake_store.get_events_for_run("run-001")
        run_002_events = await fake_store.get_events_for_run("run-002")

        # Assert
        assert len(run_001_events) == 2
        assert len(run_002_events) == 1

    @pytest.mark.asyncio
    async def test_returns_tuple_type(self) -> None:
        # Arrange
        fake_store = FakeEventStore()
        await fake_store.append_event(_make_event("run-001", "pipeline.run_created"))

        # Act
        events = await fake_store.get_events_for_run("run-001")

        # Assert
        assert isinstance(events, tuple)


class TestFakeEventStoreGetEventCount:
    """Verify get_event_count_for_run returns correct counts."""

    @pytest.mark.asyncio
    async def test_returns_zero_for_unknown_run(self) -> None:
        # Arrange
        fake_store = FakeEventStore()

        # Act
        count = await fake_store.get_event_count_for_run("nonexistent-run")

        # Assert
        assert count == 0

    @pytest.mark.asyncio
    async def test_counts_only_matching_run_events(self) -> None:
        # Arrange
        fake_store = FakeEventStore()
        await fake_store.append_event(_make_event("run-001", "pipeline.run_created"))
        await fake_store.append_event(_make_event("run-001", "pipeline.stage_entered"))
        await fake_store.append_event(_make_event("run-002", "pipeline.run_created"))

        # Act
        count = await fake_store.get_event_count_for_run("run-001")

        # Assert
        assert count == 2
