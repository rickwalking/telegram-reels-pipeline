"""Tests for ManifestBuildHook — build unified cutaway manifest before Assembly."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.hooks.manifest_hook import ManifestBuildHook
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


def _write_encoding_plan(workspace: Path, commands: list[dict[str, object]] | None = None) -> Path:
    """Write a minimal encoding-plan.json to the workspace."""
    plan = {
        "commands": commands or [
            {
                "start_s": 0.0,
                "end_s": 30.0,
                "transcript_text": "Hello world",
                "input": "source_video.mp4",
                "output": "segment-001.mp4",
                "start_seconds": 0.0,
                "end_seconds": 30.0,
                "crop_filter": "crop=1080:1920:420:0",
            },
            {
                "start_s": 30.0,
                "end_s": 60.0,
                "transcript_text": "Second segment",
                "input": "source_video.mp4",
                "output": "segment-002.mp4",
                "start_seconds": 30.0,
                "end_seconds": 60.0,
                "crop_filter": "crop=1080:1920:420:0",
            },
        ],
        "total_duration_seconds": 60.0,
    }
    plan_path = workspace / "encoding-plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    return plan_path


# --- TestShouldRun ---


class TestManifestBuildHookShouldRun:
    """Verify should_run gating logic."""

    def test_true_for_assembly_pre(self) -> None:
        """should_run returns True for Assembly + pre."""
        hook = ManifestBuildHook()
        assert hook.should_run(PipelineStage.ASSEMBLY, "pre") is True

    def test_false_for_wrong_stage(self) -> None:
        """should_run returns False for non-Assembly stages."""
        hook = ManifestBuildHook()
        assert hook.should_run(PipelineStage.CONTENT, "pre") is False
        assert hook.should_run(PipelineStage.ROUTER, "pre") is False
        assert hook.should_run(PipelineStage.FFMPEG_ENGINEER, "pre") is False

    def test_false_for_wrong_phase(self) -> None:
        """should_run returns False for post phase."""
        hook = ManifestBuildHook()
        assert hook.should_run(PipelineStage.ASSEMBLY, "post") is False

    def test_satisfies_stage_hook_protocol(self) -> None:
        """ManifestBuildHook satisfies the StageHook protocol."""
        hook = ManifestBuildHook()
        assert isinstance(hook, StageHook)


# --- TestExecute ---


class TestManifestBuildHookExecute:
    """Verify execute behavior."""

    @pytest.mark.asyncio
    async def test_execute_with_valid_encoding_plan(self, tmp_path: Path) -> None:
        """execute reads encoding plan, builds manifest, and writes JSON."""
        _write_encoding_plan(tmp_path)
        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        # Mock the ManifestBuilder to avoid real B-roll resolution
        fake_manifest = MagicMock()
        fake_manifest.clips = ()
        fake_builder = MagicMock()
        fake_builder.build = AsyncMock(return_value=(fake_manifest, ()))
        fake_builder.write_manifest = AsyncMock(return_value=tmp_path / "cutaway-manifest.json")

        with patch(
            "pipeline.application.manifest_builder.ManifestBuilder",
            return_value=fake_builder,
        ), patch(
            "pipeline.application.broll_placer.BrollPlacer",
        ):
            await hook.execute(ctx)

        # Verify ManifestBuilder.build was called with extracted segments
        fake_builder.build.assert_awaited_once()
        call_args = fake_builder.build.call_args
        segments = call_args[0][1]  # second positional arg
        assert len(segments) == 2
        assert segments[0]["start_s"] == 0.0
        assert segments[0]["end_s"] == 30.0
        assert segments[1]["transcript_text"] == "Second segment"

    @pytest.mark.asyncio
    async def test_execute_with_missing_encoding_plan(self, tmp_path: Path) -> None:
        """execute returns gracefully when encoding-plan.json is missing."""
        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        # No encoding-plan.json exists — should return silently
        await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json(self, tmp_path: Path) -> None:
        """execute handles invalid JSON gracefully."""
        (tmp_path / "encoding-plan.json").write_text("NOT VALID JSON", encoding="utf-8")
        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        # Should not raise
        await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_handles_builder_exception(self, tmp_path: Path) -> None:
        """execute catches ManifestBuilder exceptions without crashing."""
        _write_encoding_plan(tmp_path)
        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        with patch(
            "pipeline.application.manifest_builder.ManifestBuilder",
            side_effect=RuntimeError("builder init failed"),
        ), patch(
            "pipeline.application.broll_placer.BrollPlacer",
        ):
            # Should not raise
            await hook.execute(ctx)

    @pytest.mark.asyncio
    async def test_execute_extracts_total_duration_from_plan(self, tmp_path: Path) -> None:
        """execute passes correct total_duration from encoding plan."""
        _write_encoding_plan(tmp_path)
        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        fake_manifest = MagicMock()
        fake_manifest.clips = ()
        fake_builder = MagicMock()
        fake_builder.build = AsyncMock(return_value=(fake_manifest, ()))
        fake_builder.write_manifest = AsyncMock(return_value=tmp_path / "cutaway-manifest.json")

        with patch(
            "pipeline.application.manifest_builder.ManifestBuilder",
            return_value=fake_builder,
        ), patch(
            "pipeline.application.broll_placer.BrollPlacer",
        ):
            await hook.execute(ctx)

        call_args = fake_builder.build.call_args
        total_duration = call_args[0][2]  # third positional arg
        assert total_duration == 60.0

    @pytest.mark.asyncio
    async def test_execute_fallback_duration_from_last_segment(self, tmp_path: Path) -> None:
        """execute falls back to last segment end_s when total_duration_seconds is 0."""
        plan = {
            "commands": [
                {"start_s": 0.0, "end_s": 45.0, "transcript_text": "test"},
            ],
            "total_duration_seconds": 0,
        }
        (tmp_path / "encoding-plan.json").write_text(json.dumps(plan), encoding="utf-8")

        hook = ManifestBuildHook()
        ctx = _make_context(workspace=tmp_path)

        fake_manifest = MagicMock()
        fake_manifest.clips = ()
        fake_builder = MagicMock()
        fake_builder.build = AsyncMock(return_value=(fake_manifest, ()))
        fake_builder.write_manifest = AsyncMock(return_value=tmp_path / "cutaway-manifest.json")

        with patch(
            "pipeline.application.manifest_builder.ManifestBuilder",
            return_value=fake_builder,
        ), patch(
            "pipeline.application.broll_placer.BrollPlacer",
        ):
            await hook.execute(ctx)

        call_args = fake_builder.build.call_args
        total_duration = call_args[0][2]
        assert total_duration == 45.0
