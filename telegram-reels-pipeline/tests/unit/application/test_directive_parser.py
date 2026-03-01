"""Tests for directive_parser — parsing router output into CreativeDirectives."""

from __future__ import annotations

import logging

from pipeline.application.directive_parser import parse_directives
from pipeline.domain.directives import (
    CreativeDirectives,
    DocumentaryClip,
    NarrativeOverride,
    OverlayImage,
    TransitionPreference,
)


class TestEmptyAndMissing:
    """Empty or missing router output returns empty CreativeDirectives."""

    def test_empty_dict_returns_empty_directives(self) -> None:
        result = parse_directives({})
        assert result == CreativeDirectives.empty()
        assert not result.has_directives

    def test_missing_all_fields_returns_empty_directives(self) -> None:
        result = parse_directives({"url": "https://example.com", "topic_focus": "test"})
        assert result.overlay_images == ()
        assert result.documentary_clips == ()
        assert result.transition_preferences == ()
        assert result.narrative_overrides == ()
        assert result.raw_instructions == ""

    def test_none_values_treated_as_missing(self) -> None:
        result = parse_directives(
            {
                "overlay_images": None,
                "documentary_clips": None,
                "transition_preferences": None,
                "narrative_overrides": None,
            }
        )
        assert not result.has_directives


class TestRawInstructions:
    """raw_instructions field populated from router output."""

    def test_instructions_string_passed_through(self) -> None:
        result = parse_directives({"instructions": "add dramatic fade transitions"})
        assert result.raw_instructions == "add dramatic fade transitions"

    def test_missing_instructions_defaults_to_empty(self) -> None:
        result = parse_directives({})
        assert result.raw_instructions == ""

    def test_non_string_instructions_coerced(self) -> None:
        result = parse_directives({"instructions": 42})
        assert result.raw_instructions == "42"


class TestOverlayImages:
    """Parsing overlay_images from router output."""

    def test_valid_overlay_image(self) -> None:
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/logo.png", "timestamp_s": 5.0, "duration_s": 3.0},
                ],
            }
        )
        assert len(result.overlay_images) == 1
        img = result.overlay_images[0]
        assert isinstance(img, OverlayImage)
        assert img.path == "/img/logo.png"
        assert img.timestamp_s == 5.0
        assert img.duration_s == 3.0

    def test_multiple_overlay_images(self) -> None:
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/a.png", "timestamp_s": 0.0, "duration_s": 2.0},
                    {"path": "/img/b.png", "timestamp_s": 10.0, "duration_s": 5.0},
                ],
            }
        )
        assert len(result.overlay_images) == 2

    def test_empty_path_skipped(self) -> None:
        """OverlayImage with empty path fails domain validation."""
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "", "timestamp_s": 5.0, "duration_s": 3.0},
                ],
            }
        )
        assert result.overlay_images == ()

    def test_negative_duration_skipped(self) -> None:
        """OverlayImage with non-positive duration_s fails domain validation."""
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/logo.png", "timestamp_s": 5.0, "duration_s": -1.0},
                ],
            }
        )
        assert result.overlay_images == ()

    def test_zero_duration_skipped(self) -> None:
        """OverlayImage with zero duration_s fails domain validation."""
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/logo.png", "timestamp_s": 5.0, "duration_s": 0},
                ],
            }
        )
        assert result.overlay_images == ()

    def test_non_list_returns_empty(self) -> None:
        result = parse_directives({"overlay_images": "not a list"})
        assert result.overlay_images == ()

    def test_non_dict_entry_skipped(self) -> None:
        result = parse_directives(
            {
                "overlay_images": ["string_entry", 42, None],
            }
        )
        assert result.overlay_images == ()


class TestDocumentaryClips:
    """Parsing documentary_clips from router output."""

    def test_valid_documentary_clip(self) -> None:
        result = parse_directives(
            {
                "documentary_clips": [
                    {"path_or_query": "mars rover landing", "placement_hint": "after intro"},
                ],
            }
        )
        assert len(result.documentary_clips) == 1
        clip = result.documentary_clips[0]
        assert isinstance(clip, DocumentaryClip)
        assert clip.path_or_query == "mars rover landing"
        assert clip.placement_hint == "after intro"

    def test_empty_path_or_query_skipped(self) -> None:
        """DocumentaryClip with empty path_or_query fails domain validation."""
        result = parse_directives(
            {
                "documentary_clips": [
                    {"path_or_query": "", "placement_hint": "after intro"},
                ],
            }
        )
        assert result.documentary_clips == ()

    def test_missing_placement_hint_defaults(self) -> None:
        result = parse_directives(
            {
                "documentary_clips": [
                    {"path_or_query": "space footage"},
                ],
            }
        )
        assert len(result.documentary_clips) == 1
        assert result.documentary_clips[0].placement_hint == ""

    def test_non_list_returns_empty(self) -> None:
        result = parse_directives({"documentary_clips": {"not": "a list"}})
        assert result.documentary_clips == ()

    def test_non_dict_entry_skipped(self) -> None:
        result = parse_directives(
            {
                "documentary_clips": [123, True],
            }
        )
        assert result.documentary_clips == ()


class TestTransitionPreferences:
    """Parsing transition_preferences from router output."""

    def test_valid_transition(self) -> None:
        result = parse_directives(
            {
                "transition_preferences": [
                    {"effect_type": "fade", "timing_s": 0.5},
                ],
            }
        )
        assert len(result.transition_preferences) == 1
        pref = result.transition_preferences[0]
        assert isinstance(pref, TransitionPreference)
        assert pref.effect_type == "fade"
        assert pref.timing_s == 0.5

    def test_empty_effect_type_skipped(self) -> None:
        """TransitionPreference with empty effect_type fails domain validation."""
        result = parse_directives(
            {
                "transition_preferences": [
                    {"effect_type": "", "timing_s": 0.5},
                ],
            }
        )
        assert result.transition_preferences == ()

    def test_negative_timing_skipped(self) -> None:
        """TransitionPreference with negative timing_s fails domain validation."""
        result = parse_directives(
            {
                "transition_preferences": [
                    {"effect_type": "wipe", "timing_s": -1.0},
                ],
            }
        )
        assert result.transition_preferences == ()

    def test_zero_timing_valid(self) -> None:
        """timing_s=0 is valid (non-negative)."""
        result = parse_directives(
            {
                "transition_preferences": [
                    {"effect_type": "dissolve", "timing_s": 0},
                ],
            }
        )
        assert len(result.transition_preferences) == 1
        assert result.transition_preferences[0].timing_s == 0.0

    def test_non_list_returns_empty(self) -> None:
        result = parse_directives({"transition_preferences": 42})
        assert result.transition_preferences == ()

    def test_non_dict_entry_skipped(self) -> None:
        result = parse_directives(
            {
                "transition_preferences": [None, "fade"],
            }
        )
        assert result.transition_preferences == ()


class TestNarrativeOverrides:
    """Parsing narrative_overrides from router output."""

    def test_valid_narrative_override(self) -> None:
        result = parse_directives(
            {
                "narrative_overrides": [
                    {"tone": "dramatic", "structure": "three-act", "pacing": "fast", "arc_changes": ""},
                ],
            }
        )
        assert len(result.narrative_overrides) == 1
        override = result.narrative_overrides[0]
        assert isinstance(override, NarrativeOverride)
        assert override.tone == "dramatic"
        assert override.structure == "three-act"
        assert override.pacing == "fast"
        assert override.arc_changes == ""

    def test_single_field_sufficient(self) -> None:
        """At least one non-empty field makes a valid NarrativeOverride."""
        result = parse_directives(
            {
                "narrative_overrides": [
                    {"tone": "calm"},
                ],
            }
        )
        assert len(result.narrative_overrides) == 1
        assert result.narrative_overrides[0].tone == "calm"

    def test_all_empty_fields_skipped(self) -> None:
        """NarrativeOverride with all empty fields fails domain validation."""
        result = parse_directives(
            {
                "narrative_overrides": [
                    {"tone": "", "structure": "", "pacing": "", "arc_changes": ""},
                ],
            }
        )
        assert result.narrative_overrides == ()

    def test_missing_fields_default_empty(self) -> None:
        """Missing fields default to empty string; at least one must be non-empty."""
        result = parse_directives(
            {
                "narrative_overrides": [
                    {"pacing": "slow"},
                ],
            }
        )
        assert len(result.narrative_overrides) == 1
        override = result.narrative_overrides[0]
        assert override.tone == ""
        assert override.structure == ""
        assert override.pacing == "slow"

    def test_non_list_returns_empty(self) -> None:
        result = parse_directives({"narrative_overrides": "not a list"})
        assert result.narrative_overrides == ()

    def test_non_dict_entry_skipped(self) -> None:
        result = parse_directives(
            {
                "narrative_overrides": [42],
            }
        )
        assert result.narrative_overrides == ()


class TestNanInfRejection:
    """Verify nan/inf values are rejected by the domain model via the parser."""

    def test_nan_timestamp_overlay_skipped(self) -> None:
        result = parse_directives(
            {"overlay_images": [{"path": "/img/a.png", "timestamp_s": float("nan"), "duration_s": 1.0}]}
        )
        assert result.overlay_images == ()

    def test_inf_timestamp_overlay_skipped(self) -> None:
        result = parse_directives(
            {"overlay_images": [{"path": "/img/a.png", "timestamp_s": float("inf"), "duration_s": 1.0}]}
        )
        assert result.overlay_images == ()

    def test_nan_duration_overlay_skipped(self) -> None:
        result = parse_directives(
            {"overlay_images": [{"path": "/img/a.png", "timestamp_s": 0.0, "duration_s": float("nan")}]}
        )
        assert result.overlay_images == ()

    def test_nan_timing_transition_skipped(self) -> None:
        result = parse_directives(
            {"transition_preferences": [{"effect_type": "fade", "timing_s": float("nan")}]}
        )
        assert result.transition_preferences == ()

    def test_inf_timing_transition_skipped(self) -> None:
        result = parse_directives(
            {"transition_preferences": [{"effect_type": "fade", "timing_s": float("inf")}]}
        )
        assert result.transition_preferences == ()

    def test_neg_inf_timing_transition_skipped(self) -> None:
        result = parse_directives(
            {"transition_preferences": [{"effect_type": "fade", "timing_s": float("-inf")}]}
        )
        assert result.transition_preferences == ()

    def test_valid_entries_survive_alongside_nan(self) -> None:
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/good.png", "timestamp_s": 1.0, "duration_s": 2.0},
                    {"path": "/img/bad.png", "timestamp_s": float("nan"), "duration_s": 1.0},
                ],
            }
        )
        assert len(result.overlay_images) == 1
        assert result.overlay_images[0].path == "/img/good.png"


class TestMixedValidAndInvalid:
    """Mixed valid/invalid entries -- only valid ones parsed."""

    def test_mixed_overlay_images(self) -> None:
        result = parse_directives(
            {
                "overlay_images": [
                    {"path": "/img/good.png", "timestamp_s": 1.0, "duration_s": 2.0},
                    "not a dict",
                    {"path": "", "timestamp_s": 0.0, "duration_s": 1.0},  # empty path
                    {"path": "/img/also_good.png", "timestamp_s": 5.0, "duration_s": 3.0},
                ],
            }
        )
        assert len(result.overlay_images) == 2
        assert result.overlay_images[0].path == "/img/good.png"
        assert result.overlay_images[1].path == "/img/also_good.png"

    def test_mixed_documentary_clips(self) -> None:
        result = parse_directives(
            {
                "documentary_clips": [
                    {"path_or_query": "valid query"},
                    {"path_or_query": ""},  # empty path_or_query
                    42,  # not a dict
                    {"path_or_query": "another valid"},
                ],
            }
        )
        assert len(result.documentary_clips) == 2

    def test_mixed_transitions(self) -> None:
        result = parse_directives(
            {
                "transition_preferences": [
                    {"effect_type": "fade", "timing_s": 0.5},
                    {"effect_type": "", "timing_s": 1.0},  # empty effect_type
                    {"effect_type": "wipe", "timing_s": 1.0},
                ],
            }
        )
        assert len(result.transition_preferences) == 2

    def test_mixed_narrative_overrides(self) -> None:
        result = parse_directives(
            {
                "narrative_overrides": [
                    {"tone": "dramatic"},
                    {"tone": "", "structure": "", "pacing": "", "arc_changes": ""},  # all empty
                    {"pacing": "slow"},
                ],
            }
        )
        assert len(result.narrative_overrides) == 2


class TestWarningLogs:
    """Invalid entries produce warning logs."""

    def test_non_dict_overlay_logs_warning(self) -> None:
        logger = logging.getLogger("pipeline.application.directive_parser")
        with _CaptureLogs(logger) as records:
            parse_directives({"overlay_images": ["not_a_dict"]})
        assert any("overlay_images[0]" in r.message for r in records)

    def test_invalid_overlay_logs_warning(self) -> None:
        logger = logging.getLogger("pipeline.application.directive_parser")
        with _CaptureLogs(logger) as records:
            parse_directives(
                {
                    "overlay_images": [{"path": "", "timestamp_s": 0, "duration_s": 1}],
                }
            )
        assert any("overlay_images[0]" in r.message for r in records)


class TestFullIntegration:
    """Full integration: all directive types at once."""

    def test_all_directive_types_together(self) -> None:
        router_output = {
            "url": "https://youtube.com/watch?v=abc",
            "topic_focus": "AI safety",
            "instructions": "make it dramatic with fade transitions",
            "overlay_images": [
                {"path": "/img/logo.png", "timestamp_s": 0.0, "duration_s": 5.0},
            ],
            "documentary_clips": [
                {"path_or_query": "mars landing footage", "placement_hint": "after intro"},
            ],
            "transition_preferences": [
                {"effect_type": "fade", "timing_s": 0.5},
                {"effect_type": "dissolve", "timing_s": 1.0},
            ],
            "narrative_overrides": [
                {"tone": "dramatic", "pacing": "fast"},
            ],
        }
        result = parse_directives(router_output)

        assert result.has_directives
        assert result.raw_instructions == "make it dramatic with fade transitions"
        assert len(result.overlay_images) == 1
        assert len(result.documentary_clips) == 1
        assert len(result.transition_preferences) == 2
        assert len(result.narrative_overrides) == 1

        assert result.overlay_images[0].path == "/img/logo.png"
        assert result.documentary_clips[0].path_or_query == "mars landing footage"
        assert result.transition_preferences[0].effect_type == "fade"
        assert result.transition_preferences[1].effect_type == "dissolve"
        assert result.narrative_overrides[0].tone == "dramatic"
        assert result.narrative_overrides[0].pacing == "fast"


# --- Helper ---


class _LogCapture(logging.Handler):
    """Minimal log handler that collects records in a list."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _CaptureLogs:
    """Context manager to capture log records from a specific logger."""

    def __init__(self, target_logger: logging.Logger) -> None:
        self._logger = target_logger
        self._handler = _LogCapture()

    def __enter__(self) -> list[logging.LogRecord]:
        self._logger.addHandler(self._handler)
        self._logger.setLevel(logging.DEBUG)
        return self._handler.records

    def __exit__(self, *args: object) -> None:
        self._logger.removeHandler(self._handler)
