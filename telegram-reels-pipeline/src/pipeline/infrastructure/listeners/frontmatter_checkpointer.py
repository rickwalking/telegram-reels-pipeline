"""FrontmatterCheckpointer — atomically update run.md on stage completion events."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from pipeline.domain.models import PipelineEvent, RunState

if TYPE_CHECKING:
    from pipeline.domain.ports import StateStorePort


class StateProvider(Protocol):
    """Protocol for objects that can supply the current RunState."""

    def get_current_state(self) -> RunState | None: ...

logger = logging.getLogger(__name__)

# Events that trigger a checkpoint write
CHECKPOINT_EVENTS: frozenset[str] = frozenset(
    {
        "pipeline.stage_completed",
        "qa.gate_passed",
    }
)


class FrontmatterCheckpointer:
    """Write RunState checkpoint to run.md on stage completion events.

    Delegates actual persistence to the StateStorePort adapter (atomic writes).
    Only triggers on events in CHECKPOINT_EVENTS.
    """

    def __init__(self, state_store: StateStorePort, state_provider: StateProvider) -> None:
        self._state_store = state_store
        self._state_provider = state_provider

    async def __call__(self, event: PipelineEvent) -> None:
        """Checkpoint RunState if this is a stage completion event."""
        if event.event_name not in CHECKPOINT_EVENTS:
            return

        state = self._state_provider.get_current_state()
        if state is None:
            logger.warning("No current state to checkpoint for event %s", event.event_name)
            return

        await self._state_store.save_state(state)
        logger.info("Checkpointed state for event %s", event.event_name)
