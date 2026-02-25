"""Tests for BrollPlacer — variant-driven B-roll placement resolution."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.application.broll_placer import BrollPlacer


def _write_jobs(workspace: Path, jobs: list[dict[str, object]]) -> None:
    """Write a veo3/jobs.json file in the workspace."""
    veo3_dir = workspace / "veo3"
    veo3_dir.mkdir(parents=True, exist_ok=True)
    (veo3_dir / "jobs.json").write_text(json.dumps({"jobs": jobs}))


def _write_assets(workspace: Path, prompts: list[dict[str, str]]) -> None:
    """Write publishing-assets.json with veo3_prompts."""
    (workspace / "publishing-assets.json").write_text(json.dumps({"veo3_prompts": prompts}))


def _write_encoding_plan(workspace: Path, commands: list[dict[str, object]]) -> None:
    """Write encoding-plan.json with segment commands."""
    (workspace / "encoding-plan.json").write_text(json.dumps({"commands": commands}))


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


class TestBrollPlacerNoVeo3:
    """When no veo3/ folder exists, returns empty."""

    def test_no_veo3_folder_returns_empty(self, tmp_path: Path) -> None:
        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)
        assert result == ()


class TestBrollPlacerNoCompleted:
    """When veo3/jobs.json exists but no completed clips, returns empty."""

    def test_no_completed_clips(self, tmp_path: Path) -> None:
        _write_jobs(
            tmp_path,
            [
                {
                    "idempotent_key": "run1_broll",
                    "variant": "broll",
                    "prompt": "a shot",
                    "status": "generating",
                    "video_path": None,
                }
            ],
        )
        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)
        assert result == ()


class TestBrollPlacerIntro:
    """Intro variant is placed at timeline t=0."""

    def test_intro_at_start(self, tmp_path: Path) -> None:
        clip = tmp_path / "intro.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("intro", str(clip))])
        _write_assets(tmp_path, [{"variant": "intro", "narrative_anchor": "hook opening"}])

        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)

        assert len(result) == 1
        assert result[0].variant == "intro"
        assert result[0].insertion_point_s == 0.0
        assert result[0].match_confidence == 1.0


class TestBrollPlacerOutro:
    """Outro variant is placed at the end of the reel."""

    def test_outro_at_end(self, tmp_path: Path) -> None:
        clip = tmp_path / "outro.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("outro", str(clip))])

        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)

        assert len(result) == 1
        assert result[0].variant == "outro"
        # Default clip duration is 6s, so insertion = 60 - 6 = 54
        assert result[0].insertion_point_s == 54.0
        assert result[0].match_confidence == 1.0


class TestBrollPlacerBrollMatch:
    """Broll variant matched via Jaccard keyword overlap."""

    def test_good_match_placed_at_segment_midpoint(self, tmp_path: Path) -> None:
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("broll", str(clip), prompt="deep neural networks architecture")])
        _write_assets(tmp_path, [{"variant": "broll", "narrative_anchor": "deep neural networks architecture layers"}])

        segments = _make_segments()
        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, segments, 60.0)

        assert len(result) == 1
        assert result[0].variant == "broll"
        assert result[0].match_confidence > 0.3
        # Should match segment 1 (index 1) which has "deep neural networks architecture layers"
        # Segment 1 midpoint is 30.0, minus half clip duration (3.0) = 27.0
        assert result[0].insertion_point_s == 27.0

    def test_weak_match_skipped(self, tmp_path: Path) -> None:
        clip = tmp_path / "broll.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("broll", str(clip), prompt="completely unrelated zebra safari")])
        _write_assets(
            tmp_path, [{"variant": "broll", "narrative_anchor": "completely unrelated zebra safari adventure"}]
        )

        segments = _make_segments()
        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, segments, 60.0)

        # All segments talk about ML/deployment, anchor is about zebras — low overlap
        assert result == ()


class TestBrollPlacerTransition:
    """Transition variant placed at segment boundaries."""

    def test_transition_at_boundary(self, tmp_path: Path) -> None:
        clip = tmp_path / "transition.mp4"
        clip.write_bytes(b"video")
        _write_jobs(tmp_path, [_make_completed_job("transition", str(clip))])
        _write_encoding_plan(
            tmp_path,
            [
                {"end_s": 20.0},
                {"end_s": 40.0},
                {"end_s": 60.0},
            ],
        )

        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)

        assert len(result) == 1
        assert result[0].variant == "transition"
        # Midpoint of reel is 30.0, closest boundary is 40.0
        # insertion = 40.0 - 3.0 (half of default 6s) = 37.0
        # But actually closest to 30.0 is 20.0 (10 away) vs 40.0 (10 away) — tie goes to min()
        # min(20, 40, 60, key=abs(b-30)) -> 20 or 40 equally close. Python min picks first = 20
        # insertion = 20.0 - 3.0 = 17.0
        assert result[0].insertion_point_s == 17.0


class TestBrollPlacerMultipleClips:
    """Multiple clips are sorted by insertion_point_s."""

    def test_sorted_by_insertion_point(self, tmp_path: Path) -> None:
        intro_clip = tmp_path / "intro.mp4"
        outro_clip = tmp_path / "outro.mp4"
        intro_clip.write_bytes(b"video")
        outro_clip.write_bytes(b"video")

        _write_jobs(
            tmp_path,
            [
                _make_completed_job("outro", str(outro_clip)),
                _make_completed_job("intro", str(intro_clip)),
            ],
        )

        placer = BrollPlacer()
        result = placer.resolve_placements(tmp_path, _make_segments(), 60.0)

        assert len(result) == 2
        assert result[0].variant == "intro"
        assert result[0].insertion_point_s == 0.0
        assert result[1].variant == "outro"
        assert result[1].insertion_point_s == 54.0
        # Confirm sorted
        assert result[0].insertion_point_s <= result[1].insertion_point_s


class TestBrollPlacerMatchAnchor:
    """Unit tests for _match_anchor static method."""

    def test_empty_anchor_returns_zero(self) -> None:
        idx, score = BrollPlacer._match_anchor("", _make_segments())
        assert idx == 0
        assert score == 0.0

    def test_exact_word_overlap(self) -> None:
        segments = [
            {"transcript_text": "alpha beta gamma"},
            {"transcript_text": "delta epsilon zeta"},
        ]
        idx, score = BrollPlacer._match_anchor("delta epsilon", segments)
        assert idx == 1
        assert score > 0.0

    def test_no_overlap_returns_low_score(self) -> None:
        segments = [{"transcript_text": "cat dog bird"}]
        _, score = BrollPlacer._match_anchor("quantum physics thermodynamics", segments)
        assert score == 0.0
