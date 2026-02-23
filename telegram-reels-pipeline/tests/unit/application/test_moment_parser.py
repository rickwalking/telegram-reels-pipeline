"""Tests for moment_parser — multi-moment, single-moment legacy, and malformed fallback."""

from __future__ import annotations

from pipeline.application.moment_parser import parse_narrative_plan
from pipeline.domain.enums import NarrativeRole


class TestMultiMomentParsing:
    def test_two_moments_parsed(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "legacy top-level",
            "moments": [
                {
                    "start_seconds": 30.0,
                    "end_seconds": 60.0,
                    "role": "intro",
                    "transcript_excerpt": "intro text",
                },
                {
                    "start_seconds": 100.0,
                    "end_seconds": 160.0,
                    "role": "core",
                    "transcript_excerpt": "core insight",
                },
            ],
        }
        plan = parse_narrative_plan(data, target_duration=120.0)
        assert plan is not None
        assert len(plan.moments) == 2
        assert plan.moments[0].role == NarrativeRole.INTRO
        assert plan.moments[1].role == NarrativeRole.CORE
        assert plan.target_duration_seconds == 120.0

    def test_five_moments_parsed_and_sorted(self) -> None:
        data = {
            "start_seconds": 10.0,
            "end_seconds": 30.0,
            "transcript_text": "legacy",
            "moments": [
                {"start_seconds": 200.0, "end_seconds": 215.0, "role": "conclusion", "transcript_excerpt": "wrap-up"},
                {"start_seconds": 100.0, "end_seconds": 160.0, "role": "core", "transcript_excerpt": "main point"},
                {"start_seconds": 10.0, "end_seconds": 25.0, "role": "intro", "transcript_excerpt": "opening"},
                {"start_seconds": 50.0, "end_seconds": 80.0, "role": "buildup", "transcript_excerpt": "tension"},
                {"start_seconds": 170.0, "end_seconds": 190.0, "role": "reaction", "transcript_excerpt": "response"},
            ],
        }
        plan = parse_narrative_plan(data, target_duration=180.0)
        assert plan is not None
        assert len(plan.moments) == 5
        roles = [m.role for m in plan.moments]
        assert roles == [
            NarrativeRole.INTRO,
            NarrativeRole.BUILDUP,
            NarrativeRole.CORE,
            NarrativeRole.REACTION,
            NarrativeRole.CONCLUSION,
        ]

    def test_transcript_text_field_also_accepted(self) -> None:
        """Parser should accept transcript_text as fallback for transcript_excerpt."""
        data = {
            "start_seconds": 0.0,
            "end_seconds": 30.0,
            "transcript_text": "legacy",
            "moments": [
                {"start_seconds": 10.0, "end_seconds": 25.0, "role": "intro", "transcript_text": "from text field"},
                {"start_seconds": 100.0, "end_seconds": 160.0, "role": "core", "transcript_excerpt": "from excerpt"},
            ],
        }
        plan = parse_narrative_plan(data, target_duration=120.0)
        assert plan is not None
        assert plan.moments[0].transcript_excerpt == "from text field"
        assert plan.moments[1].transcript_excerpt == "from excerpt"


class TestSingleMomentLegacy:
    def test_legacy_format_produces_single_core_moment(self) -> None:
        data = {
            "start_seconds": 120.0,
            "end_seconds": 200.0,
            "transcript_text": "The main insight here is...",
            "rationale": "Best moment in episode",
            "topic_match_score": 0.85,
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1
        assert plan.moments[0].role == NarrativeRole.CORE
        assert plan.moments[0].start_seconds == 120.0
        assert plan.moments[0].end_seconds == 200.0

    def test_legacy_with_empty_moments_array(self) -> None:
        data = {
            "start_seconds": 50.0,
            "end_seconds": 110.0,
            "transcript_text": "Some text",
            "moments": [],
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1
        assert plan.moments[0].role == NarrativeRole.CORE

    def test_legacy_with_single_item_moments_array(self) -> None:
        """Single-item moments array falls through to legacy path."""
        data = {
            "start_seconds": 50.0,
            "end_seconds": 110.0,
            "transcript_text": "Some text",
            "moments": [
                {"start_seconds": 50.0, "end_seconds": 110.0, "role": "core", "transcript_excerpt": "text"},
            ],
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1


class TestMalformedFallback:
    def test_invalid_moments_falls_back_to_single(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "fallback text",
            "moments": [
                {"bad_field": "no start_seconds"},
                {"also_bad": "missing everything"},
            ],
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1
        assert plan.moments[0].role == NarrativeRole.CORE

    def test_moments_with_invalid_roles_falls_back(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "fallback text",
            "moments": [
                {"start_seconds": 10.0, "end_seconds": 30.0, "role": "INVALID", "transcript_excerpt": "text"},
                {"start_seconds": 50.0, "end_seconds": 80.0, "role": "core", "transcript_excerpt": "text"},
            ],
        }
        # One valid moment parsed (core), NarrativePlan(1 core) succeeds directly
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1
        assert plan.moments[0].role == NarrativeRole.CORE

    def test_duplicate_core_roles_falls_back(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "fallback text",
            "moments": [
                {"start_seconds": 10.0, "end_seconds": 40.0, "role": "core", "transcript_excerpt": "a"},
                {"start_seconds": 50.0, "end_seconds": 80.0, "role": "core", "transcript_excerpt": "b"},
            ],
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        # Falls back to single-moment from top-level
        assert len(plan.moments) == 1
        assert plan.moments[0].role == NarrativeRole.CORE

    def test_completely_invalid_data_returns_none(self) -> None:
        data = {"unrelated": "data", "no_timestamps": True}
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is None

    def test_moments_not_a_list_falls_back(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "text",
            "moments": "not a list",
        }
        plan = parse_narrative_plan(data, target_duration=90.0)
        assert plan is not None
        assert len(plan.moments) == 1

    def test_default_target_duration(self) -> None:
        data = {
            "start_seconds": 100.0,
            "end_seconds": 160.0,
            "transcript_text": "text",
        }
        plan = parse_narrative_plan(data)
        assert plan is not None
        assert plan.target_duration_seconds == 90.0
