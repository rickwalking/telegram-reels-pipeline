"""DownloadOutputDTO — Pydantic DTO for video download stage output."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DownloadOutputDTO(BaseModel):
    """Output data transfer object for the video download stage.

    Carries paths to all downloaded artifacts and video metadata.
    Strict mode enforces exact field types with no coercion.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    video_file_path: str
    audio_file_path: str
    subtitle_file_path: str
    video_title: str
    video_duration_seconds: float
