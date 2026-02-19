"""Tests for content_parser — parsing AI agent JSON output into ContentPackage."""

from __future__ import annotations

import json

import pytest

from pipeline.infrastructure.adapters.content_parser import parse_content_output


class TestParseContentOutput:
    def test_valid_full_output(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["Desc A", "Desc B", "Desc C"],
                "hashtags": ["#podcast", "#tech"],
                "music_suggestion": "Lo-fi hip hop beats",
                "mood_category": "thoughtful",
            }
        )
        result = parse_content_output(raw)
        assert result.descriptions == ("Desc A", "Desc B", "Desc C")
        assert result.hashtags == ("#podcast", "#tech")
        assert result.music_suggestion == "Lo-fi hip hop beats"
        assert result.mood_category == "thoughtful"

    def test_minimal_valid_output(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["Only option"],
                "hashtags": [],
                "music_suggestion": "Ambient track",
            }
        )
        result = parse_content_output(raw)
        assert result.descriptions == ("Only option",)
        assert result.hashtags == ()
        assert result.music_suggestion == "Ambient track"
        assert result.mood_category == ""

    def test_descriptions_are_tuples(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["A", "B"],
                "hashtags": ["#tag"],
                "music_suggestion": "Beat",
            }
        )
        result = parse_content_output(raw)
        assert isinstance(result.descriptions, tuple)
        assert isinstance(result.hashtags, tuple)

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_content_output("not json {{{")

    def test_non_object_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_content_output(json.dumps([1, 2, 3]))

    def test_missing_descriptions_raises(self) -> None:
        raw = json.dumps(
            {
                "hashtags": ["#tag"],
                "music_suggestion": "Beat",
            }
        )
        with pytest.raises(ValueError, match="descriptions"):
            parse_content_output(raw)

    def test_empty_descriptions_raises(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [],
                "hashtags": [],
                "music_suggestion": "Beat",
            }
        )
        with pytest.raises(ValueError, match="descriptions"):
            parse_content_output(raw)

    def test_descriptions_not_list_raises(self) -> None:
        raw = json.dumps(
            {
                "descriptions": "single string",
                "hashtags": [],
                "music_suggestion": "Beat",
            }
        )
        with pytest.raises(ValueError, match="descriptions"):
            parse_content_output(raw)

    def test_hashtags_not_list_raises(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["Desc"],
                "hashtags": "not a list",
                "music_suggestion": "Beat",
            }
        )
        with pytest.raises(ValueError, match="hashtags"):
            parse_content_output(raw)

    def test_missing_music_suggestion_raises(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["Desc"],
                "hashtags": [],
            }
        )
        with pytest.raises(ValueError, match="music_suggestion"):
            parse_content_output(raw)

    def test_empty_music_suggestion_raises(self) -> None:
        raw = json.dumps(
            {
                "descriptions": ["Desc"],
                "hashtags": [],
                "music_suggestion": "",
            }
        )
        with pytest.raises(ValueError, match="music_suggestion"):
            parse_content_output(raw)

    def test_non_string_descriptions_coerced(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [123, True],
                "hashtags": [456],
                "music_suggestion": "Beat",
            }
        )
        result = parse_content_output(raw)
        assert result.descriptions == ("123", "True")
        assert result.hashtags == ("456",)
