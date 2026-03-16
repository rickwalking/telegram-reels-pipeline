"""VideoGenerationPort — protocol for generating short video clips via Veo 3 API."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import Veo3Job, Veo3Prompt


@runtime_checkable
class VideoGenerationPort(Protocol):
    """Generate short video clips via Veo 3 API for B-roll and transitions."""

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a video generation job with the given prompt.

        Args:
            prompt: Veo3Prompt specifying variant, text, and duration.

        Returns:
            Veo3Job tracking the submitted job with initial GENERATING status.
            The returned job includes ``operation_name`` for later polling
            and authenticated download via the Gemini API.
        """
        ...

    async def poll_job(self, idempotent_key: str) -> Veo3Job:
        """Poll the status of a previously submitted job.

        Args:
            idempotent_key: The idempotent key returned from submit_job.

        Returns:
            Updated Veo3Job with current status and video_path (if completed).
        """
        ...

    async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
        """Download a completed video clip to the specified destination.

        Args:
            job: Veo3Job with status COMPLETED and video_path set.
            dest: Destination Path where the clip should be written.

        Returns:
            Path to the downloaded file (same as dest).
        """
        ...
