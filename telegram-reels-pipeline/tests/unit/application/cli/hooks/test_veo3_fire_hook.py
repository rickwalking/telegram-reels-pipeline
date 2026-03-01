"""Tests for Veo3FireHook — fire Veo3 B-roll generation after Content stage."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.hooks.veo3_fire_hook import Veo3FireHook
from pipeline.application.cli.protocols import StageHook
from pipeline.domain.enums import PipelineStage

# --- Helpers ---


def _make_context(workspace: Path | None = None) -> PipelineContext:
    settings = MagicMock()
    settings.veo3_clip_count = 3
    settings.veo3_timeout_s = 300
    return PipelineContext(
        settings=settings,
        stage_runner=MagicMock(),
        event_bus=MagicMock(),
        workspace=workspace,
    )


def _make_fake_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.submit_job = AsyncMock()
    adapter.poll_job = AsyncMock()
    return adapter


# --- TestShouldRun ---


class TestVeo3FireHookShouldRun:
    """Verify should_run gating logic."""

    def test_true_for_content_post_with_adapter(self) -> None:
        """should_run returns True for Content + post when adapter is present."""
        hook = Veo3FireHook(veo3_adapter=_make_fake_adapter())
        assert hook.should_run(PipelineStage.CONTENT, "post") is True

    def test_false_when_no_adapter(self) -> None:
        """should_run returns False when adapter is None."""
        hook = Veo3FireHook(veo3_adapter=None)
        assert hook.should_run(PipelineStage.CONTENT, "post") is False

    def test_false_for_wrong_stage(self) -> None:
        """should_run returns False for non-Content stages."""
        hook = Veo3FireHook(veo3_adapter=_make_fake_adapter())
        assert hook.should_run(PipelineStage.ROUTER, "post") is False
        assert hook.should_run(PipelineStage.ASSEMBLY, "post") is False
        assert hook.should_run(PipelineStage.FFMPEG_ENGINEER, "post") is False

    def test_false_for_wrong_phase(self) -> None:
        """should_run returns False for pre phase."""
        hook = Veo3FireHook(veo3_adapter=_make_fake_adapter())
        assert hook.should_run(PipelineStage.CONTENT, "pre") is False

    def test_satisfies_stage_hook_protocol(self) -> None:
        """Veo3FireHook satisfies the StageHook protocol."""
        hook = Veo3FireHook(veo3_adapter=None)
        assert isinstance(hook, StageHook)


# --- TestExecute ---


class TestVeo3FireHookExecute:
    """Verify execute behavior."""

    @pytest.mark.asyncio
    async def test_execute_with_adapter_starts_background_task(self, tmp_path: Path) -> None:
        """execute creates a background task and stores it in context.state."""
        adapter = _make_fake_adapter()
        hook = Veo3FireHook(veo3_adapter=adapter)
        ctx = _make_context(workspace=tmp_path)

        # Patch Veo3Orchestrator to avoid real network calls
        fake_orch = MagicMock()
        fake_orch.start_generation = AsyncMock(return_value=None)

        with patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
            return_value=fake_orch,
        ):
            await hook.execute(ctx)

        assert "veo3_task" in ctx.state
        task = ctx.state["veo3_task"]
        assert isinstance(task, asyncio.Task)
        # Wait for the background task to complete
        await task

    @pytest.mark.asyncio
    async def test_execute_with_none_adapter_is_noop(self, tmp_path: Path) -> None:
        """execute with None adapter returns immediately without side effects."""
        hook = Veo3FireHook(veo3_adapter=None)
        ctx = _make_context(workspace=tmp_path)

        await hook.execute(ctx)

        assert "veo3_task" not in ctx.state

    @pytest.mark.asyncio
    async def test_execute_handles_exception_gracefully(self, tmp_path: Path) -> None:
        """execute catches orchestrator exceptions and does not crash."""
        adapter = _make_fake_adapter()
        hook = Veo3FireHook(veo3_adapter=adapter)
        ctx = _make_context(workspace=tmp_path)

        with patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
            side_effect=RuntimeError("orchestrator init failed"),
        ):
            # Should not raise
            await hook.execute(ctx)

        # No task stored on failure
        assert "veo3_task" not in ctx.state
