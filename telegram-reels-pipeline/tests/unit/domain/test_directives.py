"""Tests for domain creative directives — frozen dataclasses, validation, factories."""

from __future__ import annotations

import pytest

from pipeline.domain.directives import (
    CreativeDirectives,
    DocumentaryClip,
    NarrativeOverride,
    OverlayImage,
    TransitionPreference,
)

# ---------------------------------------------------------------------------
# OverlayImage
# ---------------------------------------------------------------------------


class TestOverlayImage:
    def test_valid_construction(self) -> None:
        # Arrange / Act
        img = OverlayImage(path="/tmp/logo.png", timestamp_s=5.0, duration_s=3.0)

        # Assert
        assert img.path == "/tmp/logo.png"
        assert img.timestamp_s == 5.0
        assert img.duration_s == 3.0

    def test_frozen(self) -> None:
        img = OverlayImage(path="/tmp/logo.png", timestamp_s=5.0, duration_s=3.0)
        with pytest.raises(AttributeError):
            img.path = "/other.png"  # type: ignore[misc]

    def test_zero_timestamp_valid(self) -> None:
        img = OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=1.0)
        assert img.timestamp_s == 0.0

    def test_empty_path_raises(self) -> None:
        with pytest.raises(ValueError, match="path must not be empty"):
            OverlayImage(path="", timestamp_s=0.0, duration_s=1.0)

    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp_s must be non-negative"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=-1.0, duration_s=1.0)

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be positive"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=0.0)

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be positive"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=-2.0)

    def test_nan_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp_s must be finite"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=float("nan"), duration_s=1.0)

    def test_inf_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp_s must be finite"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=float("inf"), duration_s=1.0)

    def test_nan_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be finite"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=float("nan"))

    def test_inf_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be finite"):
            OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=float("inf"))


# ---------------------------------------------------------------------------
# DocumentaryClip
# ---------------------------------------------------------------------------


class TestDocumentaryClip:
    def test_valid_construction(self) -> None:
        clip = DocumentaryClip(path_or_query="nature footage", placement_hint="after intro")

        assert clip.path_or_query == "nature footage"
        assert clip.placement_hint == "after intro"

    def test_default_placement_hint(self) -> None:
        clip = DocumentaryClip(path_or_query="space launch")
        assert clip.placement_hint == ""

    def test_frozen(self) -> None:
        clip = DocumentaryClip(path_or_query="nature footage")
        with pytest.raises(AttributeError):
            clip.path_or_query = "other"  # type: ignore[misc]

    def test_empty_path_or_query_raises(self) -> None:
        with pytest.raises(ValueError, match="path_or_query must not be empty"):
            DocumentaryClip(path_or_query="")


# ---------------------------------------------------------------------------
# TransitionPreference
# ---------------------------------------------------------------------------


class TestTransitionPreference:
    def test_valid_construction(self) -> None:
        pref = TransitionPreference(effect_type="fade", timing_s=0.5)

        assert pref.effect_type == "fade"
        assert pref.timing_s == 0.5

    def test_default_timing(self) -> None:
        pref = TransitionPreference(effect_type="dissolve")
        assert pref.timing_s == 0.0

    def test_frozen(self) -> None:
        pref = TransitionPreference(effect_type="wipe")
        with pytest.raises(AttributeError):
            pref.effect_type = "fade"  # type: ignore[misc]

    def test_empty_effect_type_raises(self) -> None:
        with pytest.raises(ValueError, match="effect_type must not be empty"):
            TransitionPreference(effect_type="")

    def test_negative_timing_raises(self) -> None:
        with pytest.raises(ValueError, match="timing_s must be non-negative"):
            TransitionPreference(effect_type="fade", timing_s=-0.1)

    def test_zero_timing_valid(self) -> None:
        pref = TransitionPreference(effect_type="fade", timing_s=0.0)
        assert pref.timing_s == 0.0

    def test_nan_timing_raises(self) -> None:
        with pytest.raises(ValueError, match="timing_s must be finite"):
            TransitionPreference(effect_type="fade", timing_s=float("nan"))

    def test_inf_timing_raises(self) -> None:
        with pytest.raises(ValueError, match="timing_s must be finite"):
            TransitionPreference(effect_type="fade", timing_s=float("inf"))

    def test_neg_inf_timing_raises(self) -> None:
        with pytest.raises(ValueError, match="timing_s must be finite"):
            TransitionPreference(effect_type="fade", timing_s=float("-inf"))


# ---------------------------------------------------------------------------
# NarrativeOverride
# ---------------------------------------------------------------------------


class TestNarrativeOverride:
    def test_tone_only(self) -> None:
        override = NarrativeOverride(tone="dramatic")

        assert override.tone == "dramatic"
        assert override.structure == ""
        assert override.pacing == ""
        assert override.arc_changes == ""

    def test_structure_only(self) -> None:
        override = NarrativeOverride(structure="three-act")
        assert override.structure == "three-act"

    def test_pacing_only(self) -> None:
        override = NarrativeOverride(pacing="fast")
        assert override.pacing == "fast"

    def test_arc_changes_only(self) -> None:
        override = NarrativeOverride(arc_changes="skip conclusion")
        assert override.arc_changes == "skip conclusion"

    def test_multiple_fields(self) -> None:
        override = NarrativeOverride(tone="calm", pacing="slow")
        assert override.tone == "calm"
        assert override.pacing == "slow"

    def test_frozen(self) -> None:
        override = NarrativeOverride(tone="dramatic")
        with pytest.raises(AttributeError):
            override.tone = "calm"  # type: ignore[misc]

    def test_all_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one narrative override field must be non-empty"):
            NarrativeOverride()

    def test_all_explicitly_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one narrative override field must be non-empty"):
            NarrativeOverride(tone="", structure="", pacing="", arc_changes="")


# ---------------------------------------------------------------------------
# CreativeDirectives
# ---------------------------------------------------------------------------


class TestCreativeDirectives:
    def test_empty_factory(self) -> None:
        directives = CreativeDirectives.empty()

        assert directives.overlay_images == ()
        assert directives.documentary_clips == ()
        assert directives.transition_preferences == ()
        assert directives.narrative_overrides == ()
        assert directives.raw_instructions == ""

    def test_has_directives_false_when_empty(self) -> None:
        directives = CreativeDirectives.empty()
        assert directives.has_directives is False

    def test_has_directives_true_with_overlay(self) -> None:
        img = OverlayImage(path="/tmp/logo.png", timestamp_s=0.0, duration_s=1.0)
        directives = CreativeDirectives(overlay_images=(img,))
        assert directives.has_directives is True

    def test_has_directives_true_with_documentary_clip(self) -> None:
        clip = DocumentaryClip(path_or_query="nature footage")
        directives = CreativeDirectives(documentary_clips=(clip,))
        assert directives.has_directives is True

    def test_has_directives_true_with_transition(self) -> None:
        pref = TransitionPreference(effect_type="fade")
        directives = CreativeDirectives(transition_preferences=(pref,))
        assert directives.has_directives is True

    def test_has_directives_true_with_narrative_override(self) -> None:
        override = NarrativeOverride(tone="dramatic")
        directives = CreativeDirectives(narrative_overrides=(override,))
        assert directives.has_directives is True

    def test_raw_instructions_alone_does_not_set_has_directives(self) -> None:
        directives = CreativeDirectives(raw_instructions="some text")
        assert directives.has_directives is False

    def test_frozen(self) -> None:
        directives = CreativeDirectives.empty()
        with pytest.raises(AttributeError):
            directives.raw_instructions = "new"  # type: ignore[misc]

    def test_default_factory_returns_tuple(self) -> None:
        directives = CreativeDirectives()
        assert isinstance(directives.overlay_images, tuple)
        assert isinstance(directives.documentary_clips, tuple)
        assert isinstance(directives.transition_preferences, tuple)
        assert isinstance(directives.narrative_overrides, tuple)

    def test_full_construction(self) -> None:
        img = OverlayImage(path="/tmp/logo.png", timestamp_s=5.0, duration_s=3.0)
        clip = DocumentaryClip(path_or_query="ocean waves")
        pref = TransitionPreference(effect_type="dissolve", timing_s=1.0)
        override = NarrativeOverride(tone="upbeat")

        directives = CreativeDirectives(
            overlay_images=(img,),
            documentary_clips=(clip,),
            transition_preferences=(pref,),
            narrative_overrides=(override,),
            raw_instructions="make it vibrant",
        )

        assert len(directives.overlay_images) == 1
        assert len(directives.documentary_clips) == 1
        assert len(directives.transition_preferences) == 1
        assert len(directives.narrative_overrides) == 1
        assert directives.raw_instructions == "make it vibrant"
        assert directives.has_directives is True

    def test_multiple_overlays(self) -> None:
        img1 = OverlayImage(path="/tmp/a.png", timestamp_s=0.0, duration_s=1.0)
        img2 = OverlayImage(path="/tmp/b.png", timestamp_s=5.0, duration_s=2.0)
        directives = CreativeDirectives(overlay_images=(img1, img2))
        assert len(directives.overlay_images) == 2
