"""Tests for EncodingPlanHook — execute FFmpeg encoding plan after FFmpeg Engineer."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.hooks.encoding_hook import EncodingPlanHook
from pipeline.application.cli.protocols import StageHook
from pipeline.domain.enums import PipelineStage

# --- Helpers ---


def _make_context(workspace: Path | None = None) -> PipelineContext:
    return PipelineContext(
        settings=MagicMock(),
        stage_runner=MagicMock(),
        event_bus=MagicMock(),
        workspace=workspace,
    )


def _make_fake_ffmpeg_adapter() -> MagicMock:
    adapter = MagicMock()
    adapter.execute_encoding_plan = AsyncMock(return_value=[])
    return adapter


def _make_fake_collector(return_value: tuple[Path, ...] = ()) -> MagicMock:
    return MagicMock(return_value=return_value)


def _write_encoding_plan(workspace: Path) -> Path:
    """Write a minimal encoding-plan.json."""
    plan = {
        "commands": [
            {
                "input": "source_video.mp4",
                "output": "segment-001.mp4",
                "start_seconds": 0.0,
                "end_seconds": 30.0,
                "crop_filter": "crop=1080:1920:420:0",
            },
        ],
    }
    plan_path = workspace / "encoding-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path


# --- TestShouldRun ---


class TestEncodingPlanHookShouldRun:
    """Verify should_run gating logic."""

    def test_true_for_ffmpeg_engineer_post(self) -> None:
        """should_run returns True for FFMPEG_ENGINEER + post."""
        hook = EncodingPlanHook(ffmpeg_adapter=_make_fake_ffmpeg_adapter(), artifact_collector=_make_fake_collector())
        assert hook.should_run(PipelineStage.FFMPEG_ENGINEER, "post") is True

    def test_false_for_wrong_stage(self) -> None:
        """should_run returns False for non-FFMPEG_ENGINEER stages."""
        hook = EncodingPlanHook(ffmpeg_adapter=_make_fake_ffmpeg_adapter(), artifact_collector=_make_fake_collector())
        assert hook.should_run(PipelineStage.CONTENT, "post") is False
        assert hook.should_run(PipelineStage.ASSEMBLY, "post") is False
        assert hook.should_run(PipelineStage.ROUTER, "post") is False

    def test_false_for_wrong_phase(self) -> None:
        """should_run returns False for pre phase."""
        hook = EncodingPlanHook(ffmpeg_adapter=_make_fake_ffmpeg_adapter(), artifact_collector=_make_fake_collector())
        assert hook.should_run(PipelineStage.FFMPEG_ENGINEER, "pre") is False

    def test_satisfies_stage_hook_protocol(self) -> None:
        """EncodingPlanHook satisfies the StageHook protocol."""
        hook = EncodingPlanHook(ffmpeg_adapter=_make_fake_ffmpeg_adapter(), artifact_collector=_make_fake_collector())
        assert isinstance(hook, StageHook)


# --- TestExecute ---


class TestEncodingPlanHookExecute:
    """Verify execute behavior."""

    @pytest.mark.asyncio
    async def test_execute_with_valid_encoding_plan(self, tmp_path: Path) -> None:
        """execute runs ffmpeg commands and re-collects artifacts."""
        _write_encoding_plan(tmp_path)
        adapter = _make_fake_ffmpeg_adapter()
        seg_path = tmp_path / "segment-001.mp4"
        seg_path.touch()
        adapter.execute_encoding_plan = AsyncMock(return_value=[seg_path])

        collector = _make_fake_collector(return_value=(seg_path,))
        hook = EncodingPlanHook(ffmpeg_adapter=adapter, artifact_collector=collector)
        ctx = _make_context(workspace=tmp_path)

        await hook.execute(ctx)

        adapter.execute_encoding_plan.assert_awaited_once()
        call_args = adapter.execute_encoding_plan.call_args
        assert call_args[0][0] == tmp_path / "encoding-plan.json"
        assert call_args[1]["workspace"] == tmp_path
        assert ctx.artifacts == (seg_path,)
        collector.assert_called_once_with(tmp_path)

    @pytest.mark.asyncio
    async def test_execute_with_missing_encoding_plan(self, tmp_path: Path) -> None:
        """execute raises RuntimeError when encoding-plan.json is missing."""
        adapter = _make_fake_ffmpeg_adapter()
        hook = EncodingPlanHook(ffmpeg_adapter=adapter, artifact_collector=_make_fake_collector())
        ctx = _make_context(workspace=tmp_path)

        with pytest.raises(RuntimeError, match="encoding-plan.json is missing"):
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_handles_ffmpeg_failure(self, tmp_path: Path) -> None:
        """execute propagates ffmpeg adapter exceptions."""
        _write_encoding_plan(tmp_path)
        adapter = _make_fake_ffmpeg_adapter()
        adapter.execute_encoding_plan = AsyncMock(
            side_effect=RuntimeError("ffmpeg crashed")
        )
        hook = EncodingPlanHook(ffmpeg_adapter=adapter, artifact_collector=_make_fake_collector())
        ctx = _make_context(workspace=tmp_path)

        with pytest.raises(RuntimeError, match="ffmpeg crashed"):
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_updates_context_artifacts(self, tmp_path: Path) -> None:
        """execute updates context.artifacts with re-collected workspace files."""
        _write_encoding_plan(tmp_path)
        adapter = _make_fake_ffmpeg_adapter()
        seg1 = tmp_path / "segment-001.mp4"
        seg2 = tmp_path / "segment-002.mp4"
        seg1.touch()
        seg2.touch()
        adapter.execute_encoding_plan = AsyncMock(return_value=[seg1, seg2])

        collected = (seg1, seg2, tmp_path / "encoding-plan.json")
        collector = _make_fake_collector(return_value=collected)
        hook = EncodingPlanHook(ffmpeg_adapter=adapter, artifact_collector=collector)
        ctx = _make_context(workspace=tmp_path)

        await hook.execute(ctx)

        assert ctx.artifacts == collected

    @pytest.mark.asyncio
    async def test_execute_prints_segment_names(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """execute prints progress and segment names."""
        _write_encoding_plan(tmp_path)
        adapter = _make_fake_ffmpeg_adapter()
        seg = tmp_path / "segment-001.mp4"
        seg.touch()
        adapter.execute_encoding_plan = AsyncMock(return_value=[seg])

        collector = _make_fake_collector(return_value=(seg,))
        hook = EncodingPlanHook(ffmpeg_adapter=adapter, artifact_collector=collector)
        ctx = _make_context(workspace=tmp_path)

        await hook.execute(ctx)

        captured = capsys.readouterr()
        assert "Executing encoding plan" in captured.out
        assert "1 segments" in captured.out
        assert "segment-001.mp4" in captured.out
