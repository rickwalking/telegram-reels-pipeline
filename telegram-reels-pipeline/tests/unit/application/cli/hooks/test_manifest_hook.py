"""Tests for ManifestBuildHook — build unified cutaway manifest before Assembly."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.hooks.manifest_hook import ManifestBuildHook, _read_user_instructed_clips
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


# --- TestReadUserInstructedClips ---


class TestReadUserInstructedClips:
    """Tests for _read_user_instructed_clips — documentary clips from router-output.json."""

    def test_no_router_output_returns_empty(self, tmp_path: Path) -> None:
        """No router-output.json → empty tuple."""
        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_no_documentary_clips_field(self, tmp_path: Path) -> None:
        """router-output.json without documentary_clips → empty tuple."""
        (tmp_path / "router-output.json").write_text(json.dumps({"url": "test"}))
        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_empty_documentary_clips(self, tmp_path: Path) -> None:
        """Empty documentary_clips array → empty tuple."""
        (tmp_path / "router-output.json").write_text(json.dumps({"documentary_clips": []}))
        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_valid_local_clip(self, tmp_path: Path) -> None:
        """Valid local file creates a CutawayClip."""
        clip_file = tmp_path / "intro.mp4"
        clip_file.write_bytes(b"fake video")
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "intro.mp4", "placement_hint": "intro"}]})
        )

        result = _read_user_instructed_clips(tmp_path, 100.0)
        assert len(result) == 1
        assert result[0].clip_path == str(clip_file)
        assert result[0].insertion_point_s == pytest.approx(5.0)  # 100 * 0.05
        assert result[0].match_confidence == 1.0
        assert result[0].source.value == "user_provided"

    def test_placement_hint_middle(self, tmp_path: Path) -> None:
        """Placement hint 'middle' maps to 50% of total duration."""
        clip_file = tmp_path / "clip.mp4"
        clip_file.write_bytes(b"fake")
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "clip.mp4", "placement_hint": "middle"}]})
        )

        result = _read_user_instructed_clips(tmp_path, 80.0)
        assert result[0].insertion_point_s == pytest.approx(40.0)

    def test_placement_hint_outro(self, tmp_path: Path) -> None:
        """Placement hint 'outro' maps to 90% of total duration."""
        clip_file = tmp_path / "outro.mp4"
        clip_file.write_bytes(b"fake")
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "outro.mp4", "placement_hint": "outro"}]})
        )

        result = _read_user_instructed_clips(tmp_path, 100.0)
        assert result[0].insertion_point_s == pytest.approx(90.0)

    def test_unknown_placement_defaults_to_midpoint(self, tmp_path: Path) -> None:
        """Unknown placement hint defaults to 50%."""
        clip_file = tmp_path / "clip.mp4"
        clip_file.write_bytes(b"fake")
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "clip.mp4", "placement_hint": "somewhere"}]})
        )

        result = _read_user_instructed_clips(tmp_path, 60.0)
        assert result[0].insertion_point_s == pytest.approx(30.0)

    def test_missing_file_skipped(self, tmp_path: Path) -> None:
        """Non-existent file path is skipped."""
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "nonexistent.mp4", "placement_hint": "intro"}]})
        )

        result = _read_user_instructed_clips(tmp_path, 60.0)
        assert result == ()

    def test_empty_path_skipped(self, tmp_path: Path) -> None:
        """Empty path_or_query is skipped."""
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": [{"path_or_query": "", "placement_hint": "intro"}]})
        )

        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_non_dict_entry_skipped(self, tmp_path: Path) -> None:
        """Non-dict entries in the array are skipped."""
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": ["not-a-dict", 42]})
        )

        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_non_list_documentary_clips(self, tmp_path: Path) -> None:
        """Non-list documentary_clips field → empty tuple."""
        (tmp_path / "router-output.json").write_text(
            json.dumps({"documentary_clips": "not-a-list"})
        )

        assert _read_user_instructed_clips(tmp_path, 60.0) == ()

    def test_multiple_clips(self, tmp_path: Path) -> None:
        """Multiple valid clips all returned."""
        for name in ("a.mp4", "b.mp4"):
            (tmp_path / name).write_bytes(b"fake")
        (tmp_path / "router-output.json").write_text(
            json.dumps({
                "documentary_clips": [
                    {"path_or_query": "a.mp4", "placement_hint": "intro"},
                    {"path_or_query": "b.mp4", "placement_hint": "outro"},
                ]
            })
        )

        result = _read_user_instructed_clips(tmp_path, 100.0)
        assert len(result) == 2
        assert result[0].insertion_point_s < result[1].insertion_point_s
