"""EventBus — in-process Observer pattern for pipeline event distribution."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from pipeline.domain.models import PipelineEvent

logger = logging.getLogger(__name__)

# Type alias for async event listeners
EventListener = Callable[[PipelineEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Publish-subscribe event bus for decoupled observability.

    Listeners are async callables that receive PipelineEvent instances.
    Listener failures are logged but never block the publisher.
    """

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    def subscribe(self, listener: EventListener) -> None:
        """Register an async listener to receive all published events."""
        self._listeners.append(listener)

    async def publish(self, event: PipelineEvent) -> None:
        """Dispatch an event to all subscribed listeners.

        Each listener is called sequentially. Failures are logged and swallowed
        so that one broken listener cannot disrupt the pipeline.
        """
        for listener in self._listeners:
            try:
                await listener(event)
            except Exception:
                logger.exception(
                    "Listener %s failed for event %s",
                    getattr(listener, "__name__", repr(listener)),
                    event.event_name,
                )

    @property
    def listener_count(self) -> int:
        """Number of registered listeners."""
        return len(self._listeners)
