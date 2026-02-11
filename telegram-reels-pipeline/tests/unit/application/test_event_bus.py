"""Tests for EventBus — in-process event publish/subscribe."""

from __future__ import annotations

from unittest.mock import AsyncMock

from pipeline.application.event_bus import EventBus
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent


def _make_event(
    name: str = "pipeline.stage_entered", stage: PipelineStage | None = PipelineStage.ROUTER
) -> PipelineEvent:
    return PipelineEvent(timestamp="2026-02-10T14:00:00Z", event_name=name, stage=stage)


class TestEventBusPublish:
    async def test_publish_calls_all_listeners(self) -> None:
        bus = EventBus()
        listener1 = AsyncMock()
        listener2 = AsyncMock()
        bus.subscribe(listener1)
        bus.subscribe(listener2)

        event = _make_event()
        await bus.publish(event)

        listener1.assert_called_once_with(event)
        listener2.assert_called_once_with(event)

    async def test_publish_with_no_listeners(self) -> None:
        bus = EventBus()
        await bus.publish(_make_event())  # Should not raise

    async def test_failing_listener_does_not_block_others(self) -> None:
        bus = EventBus()
        failing = AsyncMock(side_effect=RuntimeError("boom"))
        passing = AsyncMock()
        bus.subscribe(failing)
        bus.subscribe(passing)

        await bus.publish(_make_event())

        failing.assert_called_once()
        passing.assert_called_once()

    async def test_multiple_events(self) -> None:
        bus = EventBus()
        listener = AsyncMock()
        bus.subscribe(listener)

        await bus.publish(_make_event("event.one"))
        await bus.publish(_make_event("event.two"))

        assert listener.call_count == 2


class TestEventBusSubscribe:
    def test_subscribe_increments_count(self) -> None:
        bus = EventBus()
        assert bus.listener_count == 0
        bus.subscribe(AsyncMock())
        assert bus.listener_count == 1
        bus.subscribe(AsyncMock())
        assert bus.listener_count == 2

    def test_same_listener_can_subscribe_multiple_times(self) -> None:
        bus = EventBus()
        listener = AsyncMock()
        bus.subscribe(listener)
        bus.subscribe(listener)
        assert bus.listener_count == 2
