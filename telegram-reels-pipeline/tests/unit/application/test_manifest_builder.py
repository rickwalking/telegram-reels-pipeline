"""Tests for ManifestBuilder — unified cutaway manifest from Veo3 + external clips."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pipeline.application.broll_placer import BrollPlacer
from pipeline.application.manifest_builder import ManifestBuilder
from pipeline.domain.models import (
    ClipSource,
    CutawayClip,
    CutawayManifest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jobs(workspace: Path, jobs: list[dict[str, object]]) -> None:
    """Write a veo3/jobs.json file in the workspace."""
    veo3_dir = workspace / "veo3"
    veo3_dir.mkdir(parents=True, exist_ok=True)
    (veo3_dir / "jobs.json").write_text(json.dumps({"jobs": jobs}))


def _write_assets(workspace: Path, prompts: list[dict[str, str]]) -> None:
    """Write publishing-assets.json with veo3_prompts."""
    (workspace / "publishing-assets.json").write_text(json.dumps({"veo3_prompts": prompts}))


def _write_assets_with_suggestions(
    workspace: Path,
    prompts: list[dict[str, str]],
    suggestions: list[dict[str, str]],
) -> None:
    """Write publishing-assets.json with veo3_prompts and external_clip_suggestions."""
    data = {
        "veo3_prompts": prompts,
        "external_clip_suggestions": suggestions,
    }
    (workspace / "publishing-assets.json").write_text(json.dumps(data))


def _write_external_clips_cli(workspace: Path, clips: list[dict[str, object]]) -> None:
    """Write external-clips.json in CLI format (top-level array)."""
    (workspace / "external-clips.json").write_text(json.dumps(clips))


def _write_external_clips_resolver(workspace: Path, clips: list[dict[str, object]]) -> None:
    """Write external-clips.json in resolver format ({"clips": [...]})."""
    (workspace / "external-clips.json").write_text(json.dumps({"clips": clips}))


def _make_completed_job(
    variant: str,
    video_path: str,
    prompt: str = "a cinematic shot",
) -> dict[str, object]:
    return {
        "idempotent_key": f"run1_{variant}",
        "variant": variant,
        "prompt": prompt,
        "status": "completed",
        "video_path": video_path,
    }


def _make_segments() -> list[dict[str, object]]:
    return [
        {"start_s": 0.0, "end_s": 20.0, "transcript_text": "machine learning models training data"},
        {"start_s": 20.0, "end_s": 40.0, "transcript_text": "deep neural networks architecture layers"},
        {"start_s": 40.0, "end_s": 60.0, "transcript_text": "deployment production scaling kubernetes"},
    ]


# ---------------------------------------------------------------------------
# Veo3 only (no external-clips.json)
# ---------------------------------------------------------------------------


class TestManifestBuilderVeo3Only:
    """Build manifest with only Veo3 clips."""

    def test_veo3_only(self, tmp_path: Path) -> None:
        # Arrange
        clip = tmp_path / "intro.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("intro", str(clip))])
        _write_assets(tmp_path, [{"variant": "intro", "narrative_anchor": "hook opening"}])
        builder = ManifestBuilder(BrollPlacer())

        # Act
        manifest, dropped = asyncio.get_event_loop().run_until_complete(builder.build(tmp_path, _make_segments(), 60.0))

        # Assert
        assert len(manifest.clips) == 1
        assert manifest.clips[0].source == ClipSource.VEO3
        assert manifest.clips[0].insertion_point_s == 0.0
        assert dropped == ()


# ---------------------------------------------------------------------------
# External only (no veo3 folder)
# ---------------------------------------------------------------------------


class TestManifestBuilderExternalOnly:
    """Build manifest with only external clips (no veo3)."""

    def test_external_cli_format(self, tmp_path: Path) -> None:
        # Arrange
        clip_dir = tmp_path / "external_clips"
        clip_dir.mkdir()
        clip = clip_dir / "cutaway-0.mp4"
        clip.write_bytes(b"video")
        _write_external_clips_cli(
            tmp_path,
            [{"clip_path": "external_clips/cutaway-0.mp4", "insertion_point_s": 15.0, "duration_s": 5.0}],
        )
        builder = ManifestBuilder(BrollPlacer())

        # Act
        manifest, dropped = asyncio.get_event_loop().run_until_complete(builder.build(tmp_path, _make_segments(), 60.0))

        # Assert
        assert len(manifest.clips) == 1
        assert manifest.clips[0].source == ClipSource.USER_PROVIDED
        assert manifest.clips[0].insertion_point_s == 15.0
        assert manifest.clips[0].duration_s == 5.0
        assert dropped == ()


# ---------------------------------------------------------------------------
# Both sources
# ---------------------------------------------------------------------------


class TestManifestBuilderBothSources:
    """Build manifest with both Veo3 and external clips."""

    def test_both_no_overlap(self, tmp_path: Path) -> None:
        # Arrange — Veo3 intro at t=0, external clip at t=30
        intro_clip = tmp_path / "intro.mp4"
        intro_clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("intro", str(intro_clip))])
        _write_assets(tmp_path, [{"variant": "intro", "narrative_anchor": "hook"}])

        clip_dir = tmp_path / "external_clips"
        clip_dir.mkdir()
        ext_clip = clip_dir / "cutaway-0.mp4"
        ext_clip.write_bytes(b"video")
        _write_external_clips_cli(
            tmp_path,
            [{"clip_path": "external_clips/cutaway-0.mp4", "insertion_point_s": 30.0, "duration_s": 5.0}],
        )
        builder = ManifestBuilder(BrollPlacer())

        # Act
        manifest, dropped = asyncio.get_event_loop().run_until_complete(builder.build(tmp_path, _make_segments(), 60.0))

        # Assert
        assert len(manifest.clips) == 2
        assert manifest.clips[0].source == ClipSource.VEO3
        assert manifest.clips[1].source == ClipSource.USER_PROVIDED
        assert dropped == ()

    def test_both_with_overlap(self, tmp_path: Path) -> None:
        # Arrange — Veo3 intro at t=0 (6s), external clip at t=3 (5s) -> overlap
        intro_clip = tmp_path / "intro.mp4"
        intro_clip.write_bytes(b"video")
        _write_jobs(
            tmp_path,
            [
                {
                    "idempotent_key": "run1_intro",
                    "variant": "intro",
                    "prompt": "a shot",
                    "status": "completed",
                    "video_path": str(intro_clip),
                    "duration_s": 6.0,
                }
            ],
        )

        _write_external_clips_cli(
            tmp_path,
            [{"clip_path": str(intro_clip), "insertion_point_s": 3.0, "duration_s": 5.0}],
        )
        builder = ManifestBuilder(BrollPlacer())

        # Act
        manifest, dropped = asyncio.get_event_loop().run_until_complete(builder.build(tmp_path, _make_segments(), 60.0))

        # Assert — one clip should be dropped due to overlap
        assert len(manifest.clips) + len(dropped) == 2
        assert len(dropped) >= 1


# ---------------------------------------------------------------------------
# Neither source (empty manifest)
# ---------------------------------------------------------------------------


class TestManifestBuilderNoSources:
    """Build manifest with no clips at all."""

    def test_neither_source(self, tmp_path: Path) -> None:
        # Arrange — no veo3 folder, no external-clips.json
        builder = ManifestBuilder(BrollPlacer())

        # Act
        manifest, dropped = asyncio.get_event_loop().run_until_complete(builder.build(tmp_path, _make_segments(), 60.0))

        # Assert
        assert manifest.clips == ()
        assert dropped == ()


# ---------------------------------------------------------------------------
# CLI format external-clips.json
# ---------------------------------------------------------------------------


class TestManifestBuilderCLIFormat:
    """Parse CLI-format external-clips.json (top-level array)."""

    def test_cli_format_with_insertion_point(self, tmp_path: Path) -> None:
        # Arrange
        _write_external_clips_cli(
            tmp_path,
            [
                {"clip_path": "/path/to/clip.mp4", "insertion_point_s": 10.0, "duration_s": 4.0},
                {"clip_path": "/path/to/clip2.mp4", "insertion_point_s": 30.0, "duration_s": 3.0},
            ],
        )

        # Act
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)

        # Assert
        assert len(clips) == 2
        assert clips[0].source == ClipSource.USER_PROVIDED
        assert clips[0].insertion_point_s == 10.0
        assert clips[0].duration_s == 4.0
        assert clips[1].insertion_point_s == 30.0

    def test_cli_format_relative_path_resolved(self, tmp_path: Path) -> None:
        # Arrange
        _write_external_clips_cli(
            tmp_path,
            [{"clip_path": "external_clips/cutaway-0.mp4", "insertion_point_s": 5.0, "duration_s": 3.0}],
        )

        # Act
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)

        # Assert
        assert len(clips) == 1
        assert str(tmp_path / "external_clips" / "cutaway-0.mp4") == clips[0].clip_path

    def test_cli_format_skips_invalid_entries(self, tmp_path: Path) -> None:
        # Arrange — one valid, one missing clip_path, one with bad duration
        _write_external_clips_cli(
            tmp_path,
            [
                {"clip_path": "/valid.mp4", "insertion_point_s": 5.0, "duration_s": 3.0},
                {"insertion_point_s": 5.0, "duration_s": 3.0},  # missing clip_path
                {"clip_path": "/bad.mp4", "insertion_point_s": 5.0, "duration_s": -1.0},  # bad duration
            ],
        )

        # Act
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)

        # Assert
        assert len(clips) == 1


# ---------------------------------------------------------------------------
# Resolver format external-clips.json
# ---------------------------------------------------------------------------


class TestManifestBuilderResolverFormat:
    """Parse resolver-format external-clips.json ({"clips": [...]})."""

    def test_resolver_format_basic(self, tmp_path: Path) -> None:
        # Arrange
        _write_external_clips_resolver(
            tmp_path,
            [
                {
                    "search_query": "neural networks tutorial",
                    "url": "https://youtube.com/watch?v=abc",
                    "local_path": "/clips/clip1.mp4",
                    "duration": 8,
                    "label": "NN tutorial",
                }
            ],
        )
        # Write publishing-assets.json with matching suggestion
        _write_assets_with_suggestions(
            tmp_path,
            [{"variant": "broll", "prompt": "a shot"}],
            [
                {
                    "search_query": "neural networks tutorial",
                    "narrative_anchor": "deep neural networks architecture layers",
                }
            ],
        )

        # Act
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)

        # Assert
        assert len(clips) == 1
        assert clips[0].source == ClipSource.EXTERNAL
        assert clips[0].clip_path == "/clips/clip1.mp4"
        assert clips[0].duration_s == 8.0

    def test_resolver_format_no_suggestions(self, tmp_path: Path) -> None:
        # Arrange — resolver clips but no publishing-assets.json
        _write_external_clips_resolver(
            tmp_path,
            [
                {
                    "search_query": "some query",
                    "local_path": "/clips/clip.mp4",
                    "duration": 5,
                    "label": "deployment production scaling",
                }
            ],
        )

        # Act
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)

        # Assert
        assert len(clips) == 1
        assert clips[0].source == ClipSource.EXTERNAL


# ---------------------------------------------------------------------------
# Missing external-clips.json (graceful return empty)
# ---------------------------------------------------------------------------


class TestManifestBuilderMissingExternalClips:
    """Gracefully handle missing external-clips.json."""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)
        assert clips == ()

    def test_corrupt_json_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "external-clips.json").write_text("not json{{{")
        clips = ManifestBuilder._read_external_clips(tmp_path, _make_segments(), 60.0)
        assert clips == ()


# ---------------------------------------------------------------------------
# Write manifest
# ---------------------------------------------------------------------------


class TestManifestBuilderWriteManifest:
    """Verify JSON structure and atomic write."""

    def test_write_manifest_structure(self, tmp_path: Path) -> None:
        # Arrange
        clip = CutawayClip(
            source=ClipSource.VEO3,
            variant="intro",
            clip_path="/path/to/clip.mp4",
            insertion_point_s=0.0,
            duration_s=6.0,
            narrative_anchor="hook",
            match_confidence=1.0,
        )
        manifest = CutawayManifest(clips=(clip,))
        dropped_clip = CutawayClip(
            source=ClipSource.EXTERNAL,
            variant="broll",
            clip_path="/path/to/dropped.mp4",
            insertion_point_s=2.0,
            duration_s=5.0,
            narrative_anchor="overlap",
            match_confidence=0.5,
        )
        builder = ManifestBuilder(BrollPlacer())

        # Act
        path = asyncio.get_event_loop().run_until_complete(builder.write_manifest(manifest, (dropped_clip,), tmp_path))

        # Assert
        assert path.exists()
        assert path.name == "cutaway-manifest.json"
        data = json.loads(path.read_text())
        assert data["total_clips"] == 1
        assert data["total_dropped"] == 1
        assert len(data["clips"]) == 1
        assert len(data["dropped"]) == 1
        assert data["clips"][0]["source"] == "veo3"
        assert data["clips"][0]["insertion_point_s"] == 0.0
        assert data["dropped"][0]["source"] == "external"

    def test_write_manifest_returns_path(self, tmp_path: Path) -> None:
        # Arrange
        manifest = CutawayManifest(clips=())
        builder = ManifestBuilder(BrollPlacer())

        # Act
        path = asyncio.get_event_loop().run_until_complete(builder.write_manifest(manifest, (), tmp_path))

        # Assert
        assert isinstance(path, Path)
        assert path == tmp_path / "cutaway-manifest.json"


# ---------------------------------------------------------------------------
# Anchor matching for resolver clips
# ---------------------------------------------------------------------------


class TestManifestBuilderAnchorMatching:
    """Test _match_anchor for resolver clips without insertion_point_s."""

    def test_good_anchor_match(self) -> None:
        segments = _make_segments()
        insertion, confidence = ManifestBuilder._match_anchor("deep neural networks architecture layers", segments)
        # Should match segment 1 (index 1): midpoint = 30.0
        assert insertion == 30.0
        assert confidence > 0.3

    def test_empty_anchor_returns_zero(self) -> None:
        insertion, confidence = ManifestBuilder._match_anchor("", _make_segments())
        assert insertion == 0.0
        assert confidence == 0.0

    def test_empty_segments_returns_zero(self) -> None:
        insertion, confidence = ManifestBuilder._match_anchor("some text", [])
        assert insertion == 0.0
        assert confidence == 0.0

    def test_weak_match_returns_low_confidence(self) -> None:
        segments = _make_segments()
        _, confidence = ManifestBuilder._match_anchor("quantum physics thermodynamics", segments)
        assert confidence < 0.3


# ---------------------------------------------------------------------------
# Read suggestions anchors
# ---------------------------------------------------------------------------


class TestManifestBuilderReadSuggestionsAnchors:
    """Test _read_suggestions_anchors from publishing-assets.json."""

    def test_reads_anchors(self, tmp_path: Path) -> None:
        _write_assets_with_suggestions(
            tmp_path,
            [{"variant": "broll", "prompt": "a shot"}],
            [
                {"search_query": "query1", "narrative_anchor": "anchor text 1"},
                {"search_query": "query2", "narrative_anchor": "anchor text 2"},
            ],
        )
        result = ManifestBuilder._read_suggestions_anchors(tmp_path)
        assert result == {"query1": "anchor text 1", "query2": "anchor text 2"}

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        result = ManifestBuilder._read_suggestions_anchors(tmp_path)
        assert result == {}

    def test_no_suggestions_key_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "publishing-assets.json").write_text(json.dumps({"veo3_prompts": []}))
        result = ManifestBuilder._read_suggestions_anchors(tmp_path)
        assert result == {}


# ---------------------------------------------------------------------------
# Pipeline runner integration
# ---------------------------------------------------------------------------


class TestPipelineRunnerCutawayManifest:
    """Test _build_cutaway_manifest in pipeline_runner.py."""

    @pytest.mark.asyncio
    async def test_build_cutaway_manifest_writes_file(self, tmp_path: Path) -> None:
        """Verify that _build_cutaway_manifest writes cutaway-manifest.json."""
        from pipeline.application.pipeline_runner import PipelineRunner

        # Write encoding-plan.json
        plan = {
            "commands": [
                {"start_s": 0.0, "end_s": 30.0, "transcript_text": "hello world"},
                {"start_s": 30.0, "end_s": 60.0, "transcript_text": "goodbye world"},
            ],
            "total_duration_seconds": 60.0,
        }
        (tmp_path / "encoding-plan.json").write_text(json.dumps(plan))

        # Write veo3 clips
        clip = tmp_path / "intro.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("intro", str(clip))])
        _write_assets(tmp_path, [{"variant": "intro", "narrative_anchor": "hook"}])

        # Create a minimal PipelineRunner
        runner = PipelineRunner(
            stage_runner=MagicMock(),
            state_store=MagicMock(),
            event_bus=MagicMock(),
            delivery_handler=None,
            workflows_dir=tmp_path,
        )

        # Act
        await runner._build_cutaway_manifest(tmp_path)

        # Assert
        manifest_path = tmp_path / "cutaway-manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["total_clips"] >= 1

    @pytest.mark.asyncio
    async def test_build_cutaway_manifest_no_encoding_plan(self, tmp_path: Path) -> None:
        """Verify graceful handling when encoding-plan.json is missing."""
        from pipeline.application.pipeline_runner import PipelineRunner

        runner = PipelineRunner(
            stage_runner=MagicMock(),
            state_store=MagicMock(),
            event_bus=MagicMock(),
            delivery_handler=None,
            workflows_dir=tmp_path,
        )

        # Should not raise — just returns silently
        await runner._build_cutaway_manifest(tmp_path)
        assert not (tmp_path / "cutaway-manifest.json").exists()

    @pytest.mark.asyncio
    async def test_build_cutaway_manifest_empty_commands(self, tmp_path: Path) -> None:
        """Verify graceful handling when encoding-plan.json has no commands."""
        from pipeline.application.pipeline_runner import PipelineRunner

        plan = {"commands": [], "total_duration_seconds": 0.0}
        (tmp_path / "encoding-plan.json").write_text(json.dumps(plan))

        runner = PipelineRunner(
            stage_runner=MagicMock(),
            state_store=MagicMock(),
            event_bus=MagicMock(),
            delivery_handler=None,
            workflows_dir=tmp_path,
        )

        await runner._build_cutaway_manifest(tmp_path)
        # Should write manifest (even if empty)
        manifest_path = tmp_path / "cutaway-manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert data["total_clips"] == 0


# ---------------------------------------------------------------------------
# Atomic write failure tests
# ---------------------------------------------------------------------------


class TestManifestBuilderAtomicWriteFailure:
    """Verify atomic write cleans up temp file and re-raises on os.replace failure."""

    def test_os_replace_failure_cleans_temp(self, tmp_path: Path) -> None:
        """When os.replace raises, temp file is cleaned up and exception re-raised."""
        from unittest.mock import patch as _patch

        manifest = CutawayManifest(clips=())

        with (
            _patch("pipeline.application.manifest_builder.os.replace", side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            ManifestBuilder._write_manifest_sync(manifest, (), tmp_path)

        # No temp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

        # No manifest written
        assert not (tmp_path / "cutaway-manifest.json").exists()
