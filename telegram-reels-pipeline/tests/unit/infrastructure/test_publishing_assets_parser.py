"""Tests for publishing_assets_parser — parse AI output into PublishingAssets."""

from __future__ import annotations

import json

import pytest

from pipeline.domain.models import PublishingAssets
from pipeline.infrastructure.adapters.publishing_assets_parser import parse_publishing_assets


def _make_valid_payload(
    descriptions: list[dict[str, str]] | None = None,
    hashtags: list[str] | None = None,
    veo3_prompts: list[dict[str, str]] | None = None,
    external_clip_suggestions: list[dict[str, object]] | None = None,
) -> str:
    data: dict[str, object] = {
        "descriptions": descriptions or [{"language": "pt-BR", "text": "Descricao 1"}],
        "hashtags": hashtags or ["#podcast", "#tech"],
        "veo3_prompts": veo3_prompts or [{"variant": "broll", "prompt": "Cinematic shot of data streams"}],
    }
    if external_clip_suggestions is not None:
        data["external_clip_suggestions"] = external_clip_suggestions
    return json.dumps(data)


class TestParsePublishingAssetsValid:
    def test_minimal_valid(self) -> None:
        result = parse_publishing_assets(_make_valid_payload())
        assert isinstance(result, PublishingAssets)
        assert len(result.descriptions) == 1
        assert result.descriptions[0].language == "pt-BR"
        assert len(result.hashtags) == 2
        assert len(result.veo3_prompts) == 1
        assert result.external_clip_suggestions == ()

    def test_multiple_descriptions(self) -> None:
        descs = [
            {"language": "pt-BR", "text": "Variante 1"},
            {"language": "pt-BR", "text": "Variante 2"},
            {"language": "pt-BR", "text": "Variante 3"},
        ]
        result = parse_publishing_assets(_make_valid_payload(descriptions=descs))
        assert len(result.descriptions) == 3

    def test_four_veo3_prompts(self) -> None:
        prompts = [
            {"variant": "intro", "prompt": "Opening shot"},
            {"variant": "broll", "prompt": "B-roll footage"},
            {"variant": "outro", "prompt": "Closing shot"},
            {"variant": "transition", "prompt": "Transition effect"},
        ]
        result = parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))
        assert len(result.veo3_prompts) == 4


class TestParsePublishingAssetsInvalidJson:
    def test_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_publishing_assets("not json")

    def test_non_object(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_publishing_assets("[1, 2, 3]")


class TestParsePublishingAssetsDescriptions:
    def test_missing_descriptions(self) -> None:
        with pytest.raises(ValueError, match="'descriptions' must be a non-empty list"):
            parse_publishing_assets(json.dumps({"hashtags": ["#a"], "veo3_prompts": []}))

    def test_empty_descriptions(self) -> None:
        data = {"descriptions": [], "hashtags": ["#a"], "veo3_prompts": [{"variant": "broll", "prompt": "t"}]}
        raw = json.dumps(data)
        with pytest.raises(ValueError, match="'descriptions' must be a non-empty list"):
            parse_publishing_assets(raw)

    def test_description_not_object(self) -> None:
        with pytest.raises(ValueError, match="descriptions\\[0\\] must be an object"):
            parse_publishing_assets(_make_valid_payload(descriptions=["just a string"]))  # type: ignore[list-item]

    def test_description_missing_language(self) -> None:
        with pytest.raises(ValueError, match="descriptions\\[0\\].language"):
            parse_publishing_assets(_make_valid_payload(descriptions=[{"text": "no lang"}]))

    def test_description_missing_text(self) -> None:
        with pytest.raises(ValueError, match="descriptions\\[0\\].text"):
            parse_publishing_assets(_make_valid_payload(descriptions=[{"language": "en"}]))


class TestParsePublishingAssetsHashtags:
    def test_missing_hashtags(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [{"language": "en", "text": "test"}],
                "veo3_prompts": [{"variant": "broll", "prompt": "test"}],
            }
        )
        with pytest.raises(ValueError, match="'hashtags' must be a non-empty list"):
            parse_publishing_assets(raw)

    def test_empty_hashtags(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [{"language": "en", "text": "test"}],
                "hashtags": [],
                "veo3_prompts": [{"variant": "broll", "prompt": "test"}],
            }
        )
        with pytest.raises(ValueError, match="'hashtags' must be a non-empty list"):
            parse_publishing_assets(raw)


class TestParsePublishingAssetsVeo3Prompts:
    def test_missing_veo3_prompts(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [{"language": "en", "text": "test"}],
                "hashtags": ["#test"],
            }
        )
        with pytest.raises(ValueError, match="'veo3_prompts' must be a non-empty list"):
            parse_publishing_assets(raw)

    def test_empty_veo3_prompts(self) -> None:
        raw = json.dumps(
            {
                "descriptions": [{"language": "en", "text": "test"}],
                "hashtags": ["#test"],
                "veo3_prompts": [],
            }
        )
        with pytest.raises(ValueError, match="'veo3_prompts' must be a non-empty list"):
            parse_publishing_assets(raw)

    def test_too_many_veo3_prompts(self) -> None:
        prompts = [{"variant": "broll", "prompt": f"p{i}"} for i in range(5)]
        with pytest.raises(ValueError, match="1-4 items"):
            parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))

    def test_invalid_variant(self) -> None:
        prompts = [{"variant": "closeup", "prompt": "test"}]
        with pytest.raises(ValueError, match="variant must be one of"):
            parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))

    def test_empty_prompt_text(self) -> None:
        prompts = [{"variant": "broll", "prompt": ""}]
        with pytest.raises(ValueError, match="veo3_prompts\\[0\\].prompt must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))

    def test_prompt_not_object(self) -> None:
        with pytest.raises(ValueError, match="veo3_prompts\\[0\\] must be an object"):
            parse_publishing_assets(_make_valid_payload(veo3_prompts=["not an object"]))  # type: ignore[list-item]

    def test_missing_broll_variant(self) -> None:
        prompts = [{"variant": "intro", "prompt": "test"}]
        with pytest.raises(ValueError, match="broll"):
            parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))


class TestParsePublishingAssetsHashtagPrefix:
    def test_hashtag_missing_hash_raises(self) -> None:
        with pytest.raises(ValueError, match="must start with '#'"):
            parse_publishing_assets(_make_valid_payload(hashtags=["podcast"]))

    def test_hashtag_with_leading_space_stripped(self) -> None:
        result = parse_publishing_assets(_make_valid_payload(hashtags=["  #podcast  "]))
        assert result.hashtags == ("#podcast",)


class TestParsePublishingAssetsSanitization:
    def test_description_whitespace_stripped(self) -> None:
        descs = [{"language": "  pt-BR  ", "text": "  descricao  "}]
        result = parse_publishing_assets(_make_valid_payload(descriptions=descs))
        assert result.descriptions[0].language == "pt-BR"
        assert result.descriptions[0].text == "descricao"

    def test_prompt_whitespace_stripped(self) -> None:
        prompts = [{"variant": "  broll  ", "prompt": "  cinematic shot  "}]
        result = parse_publishing_assets(_make_valid_payload(veo3_prompts=prompts))
        assert result.veo3_prompts[0].variant == "broll"
        assert result.veo3_prompts[0].prompt == "cinematic shot"


def _make_suggestion(
    search_query: str = "SpaceX rocket landing slow motion",
    narrative_anchor: str = "they talk about the rocket landing",
    expected_content: str = "Footage of a SpaceX booster landing",
    duration_s: int = 8,
    insertion_point_description: str = "After the host describes the landing",
) -> dict[str, object]:
    return {
        "search_query": search_query,
        "narrative_anchor": narrative_anchor,
        "expected_content": expected_content,
        "duration_s": duration_s,
        "insertion_point_description": insertion_point_description,
    }


class TestExternalClipSuggestionsValid:
    def test_single_suggestion(self) -> None:
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[_make_suggestion()]))
        assert len(result.external_clip_suggestions) == 1
        assert result.external_clip_suggestions[0]["search_query"] == "SpaceX rocket landing slow motion"
        assert result.external_clip_suggestions[0]["narrative_anchor"] == "they talk about the rocket landing"

    def test_three_suggestions(self) -> None:
        suggestions = [
            _make_suggestion(search_query="query 1", narrative_anchor="anchor 1"),
            _make_suggestion(search_query="query 2", narrative_anchor="anchor 2"),
            _make_suggestion(search_query="query 3", narrative_anchor="anchor 3"),
        ]
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=suggestions))
        assert len(result.external_clip_suggestions) == 3

    def test_empty_list_returns_empty_tuple(self) -> None:
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[]))
        assert result.external_clip_suggestions == ()

    def test_missing_key_returns_empty_tuple(self) -> None:
        """Backward compatibility: no external_clip_suggestions key at all."""
        result = parse_publishing_assets(_make_valid_payload())
        assert result.external_clip_suggestions == ()

    def test_minimal_suggestion_only_required_fields(self) -> None:
        suggestion = {"search_query": "AI ethics debate", "narrative_anchor": "when they discuss bias"}
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))
        assert len(result.external_clip_suggestions) == 1
        assert result.external_clip_suggestions[0]["search_query"] == "AI ethics debate"
        assert "expected_content" not in result.external_clip_suggestions[0]
        assert "duration_s" not in result.external_clip_suggestions[0]

    def test_duration_s_at_boundaries(self) -> None:
        low = _make_suggestion(duration_s=3)
        high = _make_suggestion(search_query="q2", narrative_anchor="a2", duration_s=15)
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[low, high]))
        assert result.external_clip_suggestions[0]["duration_s"] == 3
        assert result.external_clip_suggestions[1]["duration_s"] == 15

    def test_whitespace_stripped(self) -> None:
        suggestion = {
            "search_query": "  rocket launch  ",
            "narrative_anchor": "  they discuss launches  ",
            "expected_content": "  footage of launch  ",
            "insertion_point_description": "  after the mention  ",
        }
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))
        s = result.external_clip_suggestions[0]
        assert s["search_query"] == "rocket launch"
        assert s["narrative_anchor"] == "they discuss launches"
        assert s["expected_content"] == "footage of launch"
        assert s["insertion_point_description"] == "after the mention"

    def test_suggestions_are_immutable_mappings(self) -> None:
        result = parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[_make_suggestion()]))
        with pytest.raises(TypeError):
            result.external_clip_suggestions[0]["new_key"] = "value"  # type: ignore[index]


class TestExternalClipSuggestionsInvalid:
    def test_too_many_suggestions(self) -> None:
        suggestions = [_make_suggestion(search_query=f"q{i}", narrative_anchor=f"a{i}") for i in range(4)]
        with pytest.raises(ValueError, match="0-3 items"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=suggestions))

    def test_missing_search_query(self) -> None:
        suggestion = {"narrative_anchor": "anchor text"}
        with pytest.raises(ValueError, match="search_query must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_empty_search_query(self) -> None:
        suggestion = {"search_query": "", "narrative_anchor": "anchor text"}
        with pytest.raises(ValueError, match="search_query must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_whitespace_only_search_query(self) -> None:
        suggestion = {"search_query": "   ", "narrative_anchor": "anchor text"}
        with pytest.raises(ValueError, match="search_query must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_missing_narrative_anchor(self) -> None:
        suggestion = {"search_query": "rocket launch"}
        with pytest.raises(ValueError, match="narrative_anchor must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_empty_narrative_anchor(self) -> None:
        suggestion = {"search_query": "rocket launch", "narrative_anchor": ""}
        with pytest.raises(ValueError, match="narrative_anchor must be a non-empty string"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_suggestion_not_object(self) -> None:
        with pytest.raises(ValueError, match="external_clip_suggestions\\[0\\] must be an object"):
            parse_publishing_assets(
                _make_valid_payload(external_clip_suggestions=["not an object"])  # type: ignore[list-item]
            )

    def test_duration_s_too_low(self) -> None:
        suggestion = _make_suggestion(duration_s=2)
        with pytest.raises(ValueError, match="duration_s must be 3-15"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_duration_s_too_high(self) -> None:
        suggestion = _make_suggestion(duration_s=16)
        with pytest.raises(ValueError, match="duration_s must be 3-15"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))

    def test_duration_s_negative(self) -> None:
        suggestion = _make_suggestion(duration_s=-1)
        with pytest.raises(ValueError, match="duration_s must be 3-15"):
            parse_publishing_assets(_make_valid_payload(external_clip_suggestions=[suggestion]))
