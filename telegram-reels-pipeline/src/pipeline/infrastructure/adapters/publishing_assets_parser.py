"""Publishing assets parser — parse AI agent output into PublishingAssets domain model."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from pipeline.domain.models import LocalizedDescription, PublishingAssets, Veo3Prompt, Veo3PromptVariant

logger = logging.getLogger(__name__)

_ALLOWED_VARIANTS: frozenset[str] = frozenset(v.value for v in Veo3PromptVariant)


def _parse_descriptions(raw: list[Any]) -> tuple[LocalizedDescription, ...]:
    """Validate and convert raw description entries."""
    descriptions: list[LocalizedDescription] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"descriptions[{i}] must be an object with 'language' and 'text'")
        language = item.get("language")
        text = item.get("text")
        if not isinstance(language, str) or not language.strip():
            raise ValueError(f"descriptions[{i}].language must be a non-empty string")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"descriptions[{i}].text must be a non-empty string")
        descriptions.append(LocalizedDescription(language=language.strip(), text=text.strip()))
    return tuple(descriptions)


def _parse_hashtags(raw: list[Any]) -> tuple[str, ...]:
    """Validate and convert raw hashtag entries."""
    hashtags: list[str] = []
    for i, tag in enumerate(raw):
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"hashtags[{i}] must be a non-empty string")
        cleaned = tag.strip()
        if not cleaned.startswith("#"):
            raise ValueError(f"hashtags[{i}] must start with '#', got '{cleaned}'")
        hashtags.append(cleaned)
    return tuple(hashtags)


def _parse_veo3_prompts(raw: list[Any]) -> tuple[Veo3Prompt, ...]:
    """Validate and convert raw Veo 3 prompt entries."""
    if len(raw) > 4:
        raise ValueError(f"'veo3_prompts' must have 1-4 items, got {len(raw)}")

    prompts: list[Veo3Prompt] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"veo3_prompts[{i}] must be an object with 'variant' and 'prompt'")
        variant = item.get("variant")
        prompt = item.get("prompt")
        if not isinstance(variant, str) or variant.strip() not in _ALLOWED_VARIANTS:
            raise ValueError(f"veo3_prompts[{i}].variant must be one of {sorted(_ALLOWED_VARIANTS)}, got '{variant}'")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"veo3_prompts[{i}].prompt must be a non-empty string")
        prompts.append(Veo3Prompt(variant=variant.strip(), prompt=prompt.strip()))
    return tuple(prompts)


def _validate_suggestion_item(i: int, item: Any) -> MappingProxyType[str, Any]:
    """Validate a single external clip suggestion and return an immutable mapping."""
    if not isinstance(item, dict):
        raise ValueError(f"external_clip_suggestions[{i}] must be an object")

    search_query = item.get("search_query")
    if not isinstance(search_query, str) or not search_query.strip():
        raise ValueError(f"external_clip_suggestions[{i}].search_query must be a non-empty string")

    narrative_anchor = item.get("narrative_anchor")
    if not isinstance(narrative_anchor, str) or not narrative_anchor.strip():
        raise ValueError(f"external_clip_suggestions[{i}].narrative_anchor must be a non-empty string")

    duration_s = item.get("duration_s")
    if duration_s is not None and (not isinstance(duration_s, (int, float)) or duration_s < 3 or duration_s > 15):
        raise ValueError(f"external_clip_suggestions[{i}].duration_s must be 3-15 when set, got {duration_s}")

    cleaned: dict[str, Any] = {"search_query": search_query.strip(), "narrative_anchor": narrative_anchor.strip()}
    expected_content = item.get("expected_content")
    if isinstance(expected_content, str) and expected_content.strip():
        cleaned["expected_content"] = expected_content.strip()
    if duration_s is not None:
        cleaned["duration_s"] = int(duration_s)
    insertion_point = item.get("insertion_point_description")
    if isinstance(insertion_point, str) and insertion_point.strip():
        cleaned["insertion_point_description"] = insertion_point.strip()
    return MappingProxyType(cleaned)


def _parse_external_clip_suggestions(raw: list[Any]) -> tuple[Mapping[str, Any], ...]:
    """Validate and convert raw external clip suggestion entries.

    Each suggestion must have ``search_query`` and ``narrative_anchor``.
    Optional fields: ``expected_content``, ``duration_s``, ``insertion_point_description``.
    Maximum 3 suggestions allowed.
    """
    if len(raw) > 3:
        raise ValueError(f"'external_clip_suggestions' must have 0-3 items, got {len(raw)}")
    return tuple(_validate_suggestion_item(i, item) for i, item in enumerate(raw))


def parse_publishing_assets(raw: str) -> PublishingAssets:
    """Parse JSON output from the content creator agent for publishing assets.

    Expected format::

        {
            "descriptions": [
                {"language": "pt-BR", "text": "Descricao do episodio..."},
                {"language": "pt-BR", "text": "Outra variante..."}
            ],
            "hashtags": ["#podcast", "#tecnologia", ...],
            "veo3_prompts": [
                {"variant": "broll", "prompt": "Cinematic slow-motion..."},
                {"variant": "intro", "prompt": "Aerial drone shot..."}
            ],
            "external_clip_suggestions": [
                {"search_query": "...", "narrative_anchor": "...", ...}
            ]
        }
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in publishing assets output: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object for publishing assets output")

    descriptions_raw = data.get("descriptions")
    if not isinstance(descriptions_raw, list) or not descriptions_raw:
        raise ValueError("'descriptions' must be a non-empty list")

    hashtags_raw = data.get("hashtags")
    if not isinstance(hashtags_raw, list) or not hashtags_raw:
        raise ValueError("'hashtags' must be a non-empty list")

    prompts_raw = data.get("veo3_prompts")
    if not isinstance(prompts_raw, list) or not prompts_raw:
        raise ValueError("'veo3_prompts' must be a non-empty list")

    suggestions_raw = data.get("external_clip_suggestions")
    suggestions: tuple[Mapping[str, Any], ...] = ()
    if isinstance(suggestions_raw, list) and suggestions_raw:
        suggestions = _parse_external_clip_suggestions(suggestions_raw)

    return PublishingAssets(
        descriptions=_parse_descriptions(descriptions_raw),
        hashtags=_parse_hashtags(hashtags_raw),
        veo3_prompts=_parse_veo3_prompts(prompts_raw),
        external_clip_suggestions=suggestions,
    )
