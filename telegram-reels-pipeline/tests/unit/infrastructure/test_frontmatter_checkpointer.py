"""Tests for FrontmatterCheckpointer — checkpoint run state on stage completion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent, RunState
from pipeline.domain.types import RunId
from pipeline.infrastructure.listeners.frontmatter_checkpointer import (
    CHECKPOINT_EVENTS,
    FrontmatterCheckpointer,
)


def _make_event(name: str = "pipeline.stage_completed") -> PipelineEvent:
    return PipelineEvent(
        timestamp="2026-02-10T14:30:00Z",
        event_name=name,
        stage=PipelineStage.ROUTER,
    )


def _make_state() -> RunState:
    return RunState(
        run_id=RunId("2026-02-10-abc123"),
        youtube_url="https://youtube.com/watch?v=test",
        current_stage=PipelineStage.RESEARCH,
    )


class TestFrontmatterCheckpointer:
    async def test_checkpoints_on_stage_completed(self) -> None:
        state = _make_state()
        state_store = AsyncMock()
        state_provider = MagicMock()
        state_provider.get_current_state.return_value = state

        checkpointer = FrontmatterCheckpointer(state_store, state_provider)
        await checkpointer(_make_event("pipeline.stage_completed"))

        state_store.save_state.assert_called_once_with(state)

    async def test_checkpoints_on_qa_gate_passed(self) -> None:
        state = _make_state()
        state_store = AsyncMock()
        state_provider = MagicMock()
        state_provider.get_current_state.return_value = state

        checkpointer = FrontmatterCheckpointer(state_store, state_provider)
        await checkpointer(_make_event("qa.gate_passed"))

        state_store.save_state.assert_called_once_with(state)

    async def test_ignores_non_checkpoint_events(self) -> None:
        state_store = AsyncMock()
        state_provider = MagicMock()

        checkpointer = FrontmatterCheckpointer(state_store, state_provider)
        await checkpointer(_make_event("pipeline.stage_entered"))

        state_store.save_state.assert_not_called()

    async def test_multiple_checkpoint_events_write_each(self) -> None:
        state = _make_state()
        state_store = AsyncMock()
        state_provider = MagicMock()
        state_provider.get_current_state.return_value = state

        checkpointer = FrontmatterCheckpointer(state_store, state_provider)
        await checkpointer(_make_event("pipeline.stage_completed"))
        await checkpointer(_make_event("qa.gate_passed"))

        assert state_store.save_state.call_count == 2

    async def test_handles_none_state(self) -> None:
        state_store = AsyncMock()
        state_provider = MagicMock()
        state_provider.get_current_state.return_value = None

        checkpointer = FrontmatterCheckpointer(state_store, state_provider)
        await checkpointer(_make_event("pipeline.stage_completed"))

        state_store.save_state.assert_not_called()

    def test_checkpoint_events_contains_expected(self) -> None:
        assert "pipeline.stage_completed" in CHECKPOINT_EVENTS
        assert "qa.gate_passed" in CHECKPOINT_EVENTS
