"""Tests for CutawayClip, resolve_overlaps, and CutawayManifest domain models."""

from __future__ import annotations

import pytest

from pipeline.domain.models import (
    BrollPlacement,
    ClipSource,
    CutawayClip,
    CutawayManifest,
    resolve_overlaps,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _clip(
    source: ClipSource = ClipSource.VEO3,
    variant: str = "broll",
    clip_path: str = "/tmp/clip.mp4",
    insertion_point_s: float = 0.0,
    duration_s: float = 5.0,
    narrative_anchor: str = "anchor",
    match_confidence: float = 0.8,
) -> CutawayClip:
    return CutawayClip(
        source=source,
        variant=variant,
        clip_path=clip_path,
        insertion_point_s=insertion_point_s,
        duration_s=duration_s,
        narrative_anchor=narrative_anchor,
        match_confidence=match_confidence,
    )


def _broll(
    variant: str = "broll",
    clip_path: str = "/tmp/broll.mp4",
    insertion_point_s: float = 0.0,
    duration_s: float = 5.0,
    narrative_anchor: str = "anchor",
    match_confidence: float = 0.8,
) -> BrollPlacement:
    return BrollPlacement(
        variant=variant,
        clip_path=clip_path,
        insertion_point_s=insertion_point_s,
        duration_s=duration_s,
        narrative_anchor=narrative_anchor,
        match_confidence=match_confidence,
    )


# ── CutawayClip ─────────────────────────────────────────────────────────────


class TestCutawayClip:
    def test_construction_valid(self) -> None:
        clip = _clip()
        assert clip.source == ClipSource.VEO3
        assert clip.variant == "broll"
        assert clip.clip_path == "/tmp/clip.mp4"
        assert clip.insertion_point_s == 0.0
        assert clip.duration_s == 5.0
        assert clip.narrative_anchor == "anchor"
        assert clip.match_confidence == 0.8

    def test_empty_clip_path_raises(self) -> None:
        with pytest.raises(ValueError, match="clip_path must not be empty"):
            _clip(clip_path="")

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be positive"):
            _clip(duration_s=-1.0)

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be positive"):
            _clip(duration_s=0.0)

    def test_confidence_below_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="match_confidence must be in"):
            _clip(match_confidence=-0.1)

    def test_confidence_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="match_confidence must be in"):
            _clip(match_confidence=1.1)

    def test_end_s_property(self) -> None:
        clip = _clip(insertion_point_s=10.0, duration_s=5.0)
        assert clip.end_s == 15.0

    def test_frozen(self) -> None:
        clip = _clip()
        with pytest.raises(AttributeError):
            clip.source = ClipSource.EXTERNAL  # type: ignore[misc]


# ── ClipSource ───────────────────────────────────────────────────────────────


class TestClipSource:
    def test_values(self) -> None:
        assert ClipSource.VEO3 == "veo3"
        assert ClipSource.EXTERNAL == "external"
        assert ClipSource.USER_PROVIDED == "user_provided"

    def test_is_str(self) -> None:
        assert isinstance(ClipSource.VEO3, str)


# ── resolve_overlaps ────────────────────────────────────────────────────────


class TestResolveOverlaps:
    def test_empty_input(self) -> None:
        kept, dropped = resolve_overlaps(())
        assert kept == ()
        assert dropped == ()

    def test_single_clip_returns_kept(self) -> None:
        clip = _clip()
        kept, dropped = resolve_overlaps((clip,))
        assert kept == (clip,)
        assert dropped == ()

    def test_no_overlaps_returns_all_kept(self) -> None:
        a = _clip(insertion_point_s=0.0, duration_s=5.0)
        b = _clip(insertion_point_s=10.0, duration_s=5.0)
        c = _clip(insertion_point_s=20.0, duration_s=5.0)

        kept, dropped = resolve_overlaps((a, b, c))
        assert len(kept) == 3
        assert len(dropped) == 0

    def test_adjacent_clips_not_overlapping(self) -> None:
        a = _clip(insertion_point_s=0.0, duration_s=5.0)
        b = _clip(insertion_point_s=5.0, duration_s=5.0)

        kept, dropped = resolve_overlaps((a, b))
        assert len(kept) == 2
        assert len(dropped) == 0

    def test_overlapping_higher_confidence_wins(self) -> None:
        loser = _clip(insertion_point_s=0.0, duration_s=10.0, match_confidence=0.5)
        winner = _clip(insertion_point_s=5.0, duration_s=10.0, match_confidence=0.9)

        kept, dropped = resolve_overlaps((loser, winner))
        assert len(kept) == 1
        assert kept[0].match_confidence == 0.9
        assert len(dropped) == 1
        assert dropped[0].match_confidence == 0.5

    def test_tie_confidence_source_priority_wins(self) -> None:
        # user_provided (priority 0) beats veo3 (priority 1)
        veo3_clip = _clip(
            source=ClipSource.VEO3,
            insertion_point_s=0.0,
            duration_s=10.0,
            match_confidence=0.8,
        )
        user_clip = _clip(
            source=ClipSource.USER_PROVIDED,
            insertion_point_s=5.0,
            duration_s=10.0,
            match_confidence=0.8,
        )

        kept, dropped = resolve_overlaps((veo3_clip, user_clip))
        assert len(kept) == 1
        assert kept[0].source == ClipSource.USER_PROVIDED
        assert len(dropped) == 1
        assert dropped[0].source == ClipSource.VEO3

    def test_tie_veo3_beats_external(self) -> None:
        veo3_clip = _clip(
            source=ClipSource.VEO3,
            insertion_point_s=0.0,
            duration_s=10.0,
            match_confidence=0.8,
        )
        ext_clip = _clip(
            source=ClipSource.EXTERNAL,
            insertion_point_s=5.0,
            duration_s=10.0,
            match_confidence=0.8,
        )

        kept, dropped = resolve_overlaps((veo3_clip, ext_clip))
        assert len(kept) == 1
        assert kept[0].source == ClipSource.VEO3

    def test_three_clips_with_chain_overlap(self) -> None:
        # a overlaps b, b overlaps c, a does not overlap c
        a = _clip(insertion_point_s=0.0, duration_s=6.0, match_confidence=0.9)
        b = _clip(insertion_point_s=5.0, duration_s=6.0, match_confidence=0.5)
        c = _clip(insertion_point_s=11.0, duration_s=5.0, match_confidence=0.7)

        kept, dropped = resolve_overlaps((a, b, c))
        # a beats b (higher confidence), c does not overlap a
        assert len(kept) == 2
        assert len(dropped) == 1
        assert dropped[0].match_confidence == 0.5


# ── CutawayManifest ─────────────────────────────────────────────────────────


class TestCutawayManifest:
    def test_empty_clips(self) -> None:
        manifest = CutawayManifest(clips=())
        assert manifest.clips == ()

    def test_sorted_clips_accepted(self) -> None:
        a = _clip(insertion_point_s=0.0)
        b = _clip(insertion_point_s=10.0)
        manifest = CutawayManifest(clips=(a, b))
        assert len(manifest.clips) == 2

    def test_unsorted_clips_raises(self) -> None:
        a = _clip(insertion_point_s=10.0)
        b = _clip(insertion_point_s=0.0)
        with pytest.raises(ValueError, match="clips must be sorted by insertion_point_s"):
            CutawayManifest(clips=(a, b))

    def test_frozen(self) -> None:
        manifest = CutawayManifest(clips=())
        with pytest.raises(AttributeError):
            manifest.clips = ()  # type: ignore[misc]


# ── from_broll_and_external ─────────────────────────────────────────────────


class TestFromBrollAndExternal:
    def test_empty_inputs(self) -> None:
        manifest, dropped = CutawayManifest.from_broll_and_external(broll=())
        assert manifest.clips == ()
        assert dropped == ()

    def test_single_broll_converts_to_veo3_clip(self) -> None:
        bp = _broll(insertion_point_s=5.0, duration_s=4.0, match_confidence=0.9)
        manifest, dropped = CutawayManifest.from_broll_and_external(broll=(bp,))
        assert len(manifest.clips) == 1
        assert dropped == ()

        clip = manifest.clips[0]
        assert clip.source == ClipSource.VEO3
        assert clip.variant == bp.variant
        assert clip.clip_path == bp.clip_path
        assert clip.insertion_point_s == bp.insertion_point_s
        assert clip.duration_s == bp.duration_s
        assert clip.narrative_anchor == bp.narrative_anchor
        assert clip.match_confidence == bp.match_confidence

    def test_merge_and_sort(self) -> None:
        bp = _broll(insertion_point_s=20.0, duration_s=5.0, match_confidence=0.8)
        ext = _clip(source=ClipSource.EXTERNAL, insertion_point_s=5.0, duration_s=3.0, match_confidence=0.7)

        manifest, dropped = CutawayManifest.from_broll_and_external(broll=(bp,), external=(ext,))
        assert len(manifest.clips) == 2
        assert dropped == ()
        # Sorted by insertion_point_s
        assert manifest.clips[0].insertion_point_s == 5.0
        assert manifest.clips[1].insertion_point_s == 20.0

    def test_overlap_resolution(self) -> None:
        bp = _broll(insertion_point_s=0.0, duration_s=10.0, match_confidence=0.9)
        ext = _clip(source=ClipSource.EXTERNAL, insertion_point_s=5.0, duration_s=10.0, match_confidence=0.5)

        manifest, dropped = CutawayManifest.from_broll_and_external(broll=(bp,), external=(ext,))
        assert len(manifest.clips) == 1
        assert manifest.clips[0].match_confidence == 0.9
        assert len(dropped) == 1

    def test_external_only(self) -> None:
        ext = _clip(source=ClipSource.USER_PROVIDED, insertion_point_s=3.0, duration_s=5.0)
        manifest, dropped = CutawayManifest.from_broll_and_external(broll=(), external=(ext,))
        assert len(manifest.clips) == 1
        assert manifest.clips[0].source == ClipSource.USER_PROVIDED
        assert dropped == ()
