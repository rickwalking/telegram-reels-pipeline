"""Content parser — parse AI agent output into ContentPackage domain model."""

from __future__ import annotations

import json
import logging

from pipeline.domain.models import ContentPackage

logger = logging.getLogger(__name__)


def parse_content_output(raw: str) -> ContentPackage:
    """Parse JSON output from the content creator agent.

    Expected format::

        {
            "descriptions": ["Option 1...", "Option 2...", "Option 3..."],
            "hashtags": ["#podcast", "#tech", ...],
            "music_suggestion": "Lo-fi hip hop beats",
            "mood_category": "thoughtful"
        }
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in content output: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object for content output")

    descriptions = data.get("descriptions")
    if not isinstance(descriptions, list) or not descriptions:
        raise ValueError("'descriptions' must be a non-empty list")

    hashtags = data.get("hashtags", [])
    if not isinstance(hashtags, list):
        raise ValueError("'hashtags' must be a list")

    music = data.get("music_suggestion", "")
    if not isinstance(music, str) or not music:
        raise ValueError("'music_suggestion' must be a non-empty string")

    return ContentPackage(
        descriptions=tuple(str(d) for d in descriptions),
        hashtags=tuple(str(h) for h in hashtags),
        music_suggestion=str(music),
        mood_category=str(data.get("mood_category", "")),
    )


