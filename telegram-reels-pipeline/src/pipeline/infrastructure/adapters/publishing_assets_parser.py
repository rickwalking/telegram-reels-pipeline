"""Publishing assets parser — parse AI agent output into PublishingAssets domain model."""

from __future__ import annotations

import json
import logging
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

    return PublishingAssets(
        descriptions=_parse_descriptions(descriptions_raw),
        hashtags=_parse_hashtags(hashtags_raw),
        veo3_prompts=_parse_veo3_prompts(prompts_raw),
    )
