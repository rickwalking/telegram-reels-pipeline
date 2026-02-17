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
) -> str:
    data = {
        "descriptions": descriptions or [{"language": "pt-BR", "text": "Descricao 1"}],
        "hashtags": hashtags or ["#podcast", "#tech"],
        "veo3_prompts": veo3_prompts or [{"variant": "broll", "prompt": "Cinematic shot of data streams"}],
    }
    return json.dumps(data)


class TestParsePublishingAssetsValid:
    def test_minimal_valid(self) -> None:
        result = parse_publishing_assets(_make_valid_payload())
        assert isinstance(result, PublishingAssets)
        assert len(result.descriptions) == 1
        assert result.descriptions[0].language == "pt-BR"
        assert len(result.hashtags) == 2
        assert len(result.veo3_prompts) == 1

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
