"""Tests for enriched veo3_prompt validation — Story 17.5.

Validates that Veo3Prompt dataclass correctly enforces the enriched prompt
contract: required fields, narrative_anchor story-language rules, duration_s
range, variant taxonomy, and intro/outro empty-anchor allowance.
"""

from __future__ import annotations

import re

import pytest

from pipeline.domain.models import Veo3Prompt, Veo3PromptVariant, make_idempotent_key

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIMESTAMP_PATTERN = re.compile(r"\d+:\d+|\d+\s*seconds?", re.IGNORECASE)


def _has_timestamp(anchor: str) -> bool:
    """Return True if the narrative_anchor contains a timestamp-like pattern."""
    return bool(_TIMESTAMP_PATTERN.search(anchor))


# ---------------------------------------------------------------------------
# Parsing enriched prompts from JSON-like dicts
# ---------------------------------------------------------------------------


class TestEnrichedPromptParsing:
    """Veo3Prompt can be constructed from enriched JSON fields."""

    def test_full_enriched_broll_prompt(self) -> None:
        """All four enriched fields parse correctly for a broll prompt."""
        long_prompt = (
            "Cinematic slow-motion shot of abstract data streams flowing"
            " through a neural network, shallow depth of field"
        )
        prompt = Veo3Prompt(
            variant="broll",
            prompt=long_prompt,
            narrative_anchor="when the host explains how neural networks process information",
            duration_s=6,
        )
        assert prompt.variant == "broll"
        assert "neural network" in prompt.prompt
        assert prompt.narrative_anchor == "when the host explains how neural networks process information"
        assert prompt.duration_s == 6

    def test_enriched_intro_prompt_empty_anchor(self) -> None:
        """Intro prompt with empty narrative_anchor is valid (placed at reel start)."""
        prompt = Veo3Prompt(
            variant="intro",
            prompt="Aerial drone shot sweeping over a futuristic cityscape at golden hour, lens flare",
            narrative_anchor="",
            duration_s=5,
        )
        assert prompt.variant == "intro"
        assert prompt.narrative_anchor == ""
        assert prompt.duration_s == 5

    def test_enriched_outro_prompt_empty_anchor(self) -> None:
        """Outro prompt with empty narrative_anchor is valid (placed at reel end)."""
        prompt = Veo3Prompt(
            variant="outro",
            prompt="Slow zoom out to wide aerial view of the city at dusk",
            narrative_anchor="",
            duration_s=7,
        )
        assert prompt.variant == "outro"
        assert prompt.narrative_anchor == ""

    def test_all_required_fields_present(self) -> None:
        """A fully specified enriched prompt has all four fields accessible."""
        prompt = Veo3Prompt(
            variant="transition",
            prompt="Quick flash cut of light particles converging, high contrast",
            narrative_anchor="during the explanation of distributed consensus",
            duration_s=5,
        )
        # All four enriched fields must be present
        assert hasattr(prompt, "variant")
        assert hasattr(prompt, "prompt")
        assert hasattr(prompt, "narrative_anchor")
        assert hasattr(prompt, "duration_s")


# ---------------------------------------------------------------------------
# narrative_anchor timestamp rejection
# ---------------------------------------------------------------------------


class TestNarrativeAnchorTimestampRejection:
    """narrative_anchor must use story language, never timestamps."""

    def test_colon_timestamp_detected(self) -> None:
        """Pattern 'at 1:23' is a timestamp and must be flagged."""
        anchor = "at 1:23 in the video"
        assert _has_timestamp(anchor)

    def test_minute_second_timestamp_detected(self) -> None:
        """Pattern '0:45' is a timestamp and must be flagged."""
        anchor = "cut to 0:45"
        assert _has_timestamp(anchor)

    def test_seconds_word_detected(self) -> None:
        """Pattern '45 seconds' is a timestamp-like reference and must be flagged."""
        anchor = "45 seconds into the clip"
        assert _has_timestamp(anchor)

    def test_seconds_word_case_insensitive(self) -> None:
        """Pattern detection is case-insensitive."""
        anchor = "30 Seconds in"
        assert _has_timestamp(anchor)

    def test_story_language_not_flagged(self) -> None:
        """Clean story-language anchor is NOT flagged as timestamp."""
        anchor = "when the host explains distributed systems"
        assert not _has_timestamp(anchor)

    def test_during_phrase_not_flagged(self) -> None:
        """'during the explanation of Y' style is valid story language."""
        anchor = "during the explanation of neural network backpropagation"
        assert not _has_timestamp(anchor)

    def test_empty_anchor_not_flagged(self) -> None:
        """Empty string is allowed (intro/outro use case)."""
        anchor = ""
        assert not _has_timestamp(anchor)

    def test_minute_mention_without_digit_not_flagged(self) -> None:
        """Mentioning 'minute' without a digit pattern is acceptable."""
        anchor = "at the pivotal minute of the conversation"
        assert not _has_timestamp(anchor)


# ---------------------------------------------------------------------------
# duration_s valid range
# ---------------------------------------------------------------------------


class TestDurationRange:
    """duration_s must be 4-8 when set; 0 means unset (backward compat)."""

    @pytest.mark.parametrize("d", [4, 5, 6, 7, 8])
    def test_valid_durations(self, d: int) -> None:
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=d)
        assert prompt.duration_s == d

    def test_duration_zero_is_allowed(self) -> None:
        """Zero is the 'unset' sentinel for backward compatibility."""
        prompt = Veo3Prompt(variant="broll", prompt="Test shot", duration_s=0)
        assert prompt.duration_s == 0

    def test_duration_below_minimum_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=3)

    def test_duration_above_maximum_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=9)

    def test_duration_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="duration_s must be 4-8"):
            Veo3Prompt(variant="broll", prompt="Test shot", duration_s=1)


# ---------------------------------------------------------------------------
# variant taxonomy
# ---------------------------------------------------------------------------


class TestVariantTaxonomy:
    """variant must be one of the four allowed values."""

    @pytest.mark.parametrize("variant", ["intro", "broll", "outro", "transition"])
    def test_valid_variants(self, variant: str) -> None:
        prompt = Veo3Prompt(variant=variant, prompt="Test cinematic shot")
        assert prompt.variant == variant

    def test_invalid_variant_rejected(self) -> None:
        with pytest.raises(ValueError, match="variant must be one of"):
            Veo3Prompt(variant="closeup", prompt="Test shot")

    def test_invalid_variant_uppercase_rejected(self) -> None:
        """Uppercase variants are not accepted — values are lowercase only."""
        with pytest.raises(ValueError, match="variant must be one of"):
            Veo3Prompt(variant="BROLL", prompt="Test shot")

    def test_enum_values_match_taxonomy(self) -> None:
        """Veo3PromptVariant enum covers exactly the four required types."""
        expected = {"intro", "broll", "outro", "transition"}
        actual = {v.value for v in Veo3PromptVariant}
        assert actual == expected


# ---------------------------------------------------------------------------
# Empty narrative_anchor allowed for intro and outro
# ---------------------------------------------------------------------------


class TestEmptyAnchorAllowance:
    """intro and outro variants permit empty narrative_anchor."""

    def test_intro_empty_anchor_valid(self) -> None:
        prompt = Veo3Prompt(variant="intro", prompt="Opening cinematic", narrative_anchor="", duration_s=5)
        assert prompt.narrative_anchor == ""

    def test_outro_empty_anchor_valid(self) -> None:
        prompt = Veo3Prompt(variant="outro", prompt="Closing cinematic", narrative_anchor="", duration_s=8)
        assert prompt.narrative_anchor == ""

    def test_broll_empty_anchor_allowed_by_model(self) -> None:
        """Domain model allows empty anchor on any variant — enforcement is agent-level."""
        prompt = Veo3Prompt(variant="broll", prompt="Abstract visualization", narrative_anchor="")
        assert prompt.narrative_anchor == ""

    def test_transition_with_story_anchor(self) -> None:
        prompt = Veo3Prompt(
            variant="transition",
            prompt="Light streak wipe, motion blur",
            narrative_anchor="when the host shifts from theory to practice",
            duration_s=5,
        )
        assert prompt.narrative_anchor == "when the host shifts from theory to practice"


# ---------------------------------------------------------------------------
# Idempotent key integration
# ---------------------------------------------------------------------------


class TestIdempotentKeyIntegration:
    """Enriched prompts work with make_idempotent_key for API deduplication."""

    def test_key_built_from_run_id_and_variant(self) -> None:
        key = make_idempotent_key("20260225-a5f7ac", "broll")
        assert key == "20260225-a5f7ac_broll"

    def test_prompt_stores_idempotent_key(self) -> None:
        key = make_idempotent_key("run-001", "intro")
        prompt = Veo3Prompt(
            variant="intro",
            prompt="Aerial establishing shot",
            narrative_anchor="",
            duration_s=5,
            idempotent_key=key,
        )
        assert prompt.idempotent_key == "run-001_intro"

    def test_all_variant_keys_are_unique(self) -> None:
        """Each variant produces a distinct idempotent key for the same run."""
        run_id = "run-42"
        keys = [make_idempotent_key(run_id, v.value) for v in Veo3PromptVariant]
        assert len(keys) == len(set(keys))
