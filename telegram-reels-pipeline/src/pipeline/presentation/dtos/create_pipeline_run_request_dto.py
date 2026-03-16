"""Presentation DTO for incoming pipeline run trigger requests."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, field_validator

YOUTUBE_URL_PATTERN: re.Pattern[str] = re.compile(
    r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]{11}"
)


class CreatePipelineRunRequestDTO(BaseModel):
    """Pydantic DTO validating inbound POST /api/runs payloads."""

    model_config = ConfigDict(strict=True, extra="forbid")

    youtube_url: str
    topic_focus: str = ""
    trigger_source: str = "api"

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, value: str) -> str:
        """Ensure the URL matches a valid YouTube video pattern."""
        if not YOUTUBE_URL_PATTERN.match(value):
            raise ValueError("youtube_url must be a valid YouTube video URL")
        return value
