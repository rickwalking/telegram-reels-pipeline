"""Tests for Veo3AwaitHook — await Veo3 B-roll completion before Assembly."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.hooks.veo3_await_hook import Veo3AwaitHook
from pipeline.application.cli.protocols import StageHook
from pipeline.domain.enums import PipelineStage

# --- Helpers ---


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.veo3_clip_count = 3
    settings.veo3_timeout_s = 300
    return settings


def _make_context(workspace: Path | None = None, **state_items: object) -> PipelineContext:
    ctx = PipelineContext(
        settings=_make_settings(),
        stage_runner=MagicMock(),
        event_bus=MagicMock(),
        workspace=workspace,
    )
    ctx.state.update(state_items)
    return ctx


def _make_fake_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.submit_job = AsyncMock()
    adapter.poll_job = AsyncMock()
    return adapter


# --- TestShouldRun ---


class TestVeo3AwaitHookShouldRun:
    """Verify should_run gating logic."""

    def test_true_for_assembly_pre(self) -> None:
        """should_run returns True for Assembly + pre."""
        hook = Veo3AwaitHook(veo3_adapter=_make_fake_adapter(), settings=_make_settings())
        assert hook.should_run(PipelineStage.ASSEMBLY, "pre") is True

    def test_true_even_without_adapter(self) -> None:
        """should_run returns True for Assembly + pre even with no adapter."""
        hook = Veo3AwaitHook(veo3_adapter=None, settings=_make_settings())
        assert hook.should_run(PipelineStage.ASSEMBLY, "pre") is True

    def test_false_for_wrong_stage(self) -> None:
        """should_run returns False for non-Assembly stages."""
        hook = Veo3AwaitHook(veo3_adapter=None, settings=_make_settings())
        assert hook.should_run(PipelineStage.CONTENT, "pre") is False
        assert hook.should_run(PipelineStage.ROUTER, "pre") is False
        assert hook.should_run(PipelineStage.FFMPEG_ENGINEER, "pre") is False

    def test_false_for_wrong_phase(self) -> None:
        """should_run returns False for post phase."""
        hook = Veo3AwaitHook(veo3_adapter=None, settings=_make_settings())
        assert hook.should_run(PipelineStage.ASSEMBLY, "post") is False

    def test_satisfies_stage_hook_protocol(self) -> None:
        """Veo3AwaitHook satisfies the StageHook protocol."""
        hook = Veo3AwaitHook(veo3_adapter=None, settings=_make_settings())
        assert isinstance(hook, StageHook)


# --- TestExecute ---


class TestVeo3AwaitHookExecute:
    """Verify execute behavior."""

    @pytest.mark.asyncio
    async def test_execute_awaits_task_from_context(self, tmp_path: Path) -> None:
        """execute awaits the veo3_task from context.state."""
        adapter = _make_fake_adapter()
        settings = _make_settings()
        hook = Veo3AwaitHook(veo3_adapter=adapter, settings=settings)

        # Create a completed task
        completed_future: asyncio.Future[None] = asyncio.get_event_loop().create_future()
        completed_future.set_result(None)
        task = asyncio.ensure_future(completed_future)

        ctx = _make_context(workspace=tmp_path, veo3_task=task)

        fake_summary = {"completed": 2, "failed": 0, "total": 2}
        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            return_value=fake_summary,
        ), patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
        ):
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_no_task_no_adapter_is_noop(self, tmp_path: Path) -> None:
        """execute with no task and no adapter runs the gate (which may skip)."""
        settings = _make_settings()
        hook = Veo3AwaitHook(veo3_adapter=None, settings=settings)
        ctx = _make_context(workspace=tmp_path)

        skip_summary = {"skipped": True, "reason": "no_veo3_folder"}
        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            return_value=skip_summary,
        ), patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
        ):
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_handles_await_gate_timeout_gracefully(self, tmp_path: Path) -> None:
        """execute catches await gate exceptions and does not crash."""
        settings = _make_settings()
        hook = Veo3AwaitHook(veo3_adapter=None, settings=settings)
        ctx = _make_context(workspace=tmp_path)

        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            side_effect=TimeoutError("gate timed out"),
        ), patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
        ):
            # Should not raise
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_handles_failed_background_task(self, tmp_path: Path) -> None:
        """execute handles a failed veo3_task without crashing."""
        adapter = _make_fake_adapter()
        settings = _make_settings()
        hook = Veo3AwaitHook(veo3_adapter=adapter, settings=settings)

        # Create a task that raises
        async def _failing_task() -> None:
            raise RuntimeError("background generation failed")

        task = asyncio.create_task(_failing_task())
        # Let the task fail
        await asyncio.sleep(0)

        ctx = _make_context(workspace=tmp_path, veo3_task=task)

        fake_summary = {"completed": 0, "failed": 1, "total": 1}
        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            return_value=fake_summary,
        ), patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
        ):
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_logs_summary_of_completed_clips(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """execute prints summary of completed/failed clips."""
        adapter = _make_fake_adapter()
        settings = _make_settings()
        hook = Veo3AwaitHook(veo3_adapter=adapter, settings=settings)
        ctx = _make_context(workspace=tmp_path)

        fake_summary = {"completed": 2, "failed": 1, "total": 3}
        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            return_value=fake_summary,
        ), patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
        ):
            await hook.execute(ctx)

        captured = capsys.readouterr()
        assert "2/3 completed" in captured.out
        assert "1 failed" in captured.out
