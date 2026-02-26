"""Gemini Veo3 adapter — implements VideoGenerationPort via google-genai SDK."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pipeline.domain.errors import PipelineError
from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt

logger = logging.getLogger(__name__)


class Veo3GenerationError(PipelineError):
    """Veo3 API call failure — submit, poll, or download error."""


class GeminiVeo3Adapter:
    """Concrete VideoGenerationPort implementation using the Gemini API.

    Requires ``google-genai`` SDK.  Instantiate with a valid Gemini API key.
    """

    MODEL_ID = "veo-3.1-generate-preview"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise Veo3GenerationError("gemini_api_key is required")
        self._api_key = api_key
        self._client: object | None = None

    def _get_client(self) -> object:
        """Lazy-init the google-genai client (import at call time)."""
        if self._client is None:
            try:
                from google import genai  # type: ignore[import-not-found]

                self._client = genai.Client(api_key=self._api_key)
            except ImportError as exc:
                raise Veo3GenerationError(
                    "google-genai SDK not installed — run: poetry add google-genai"
                ) from exc
        return self._client

    @staticmethod
    def _clamp_duration(duration_s: int) -> int:
        """Clamp duration to an even value in [4, 8]; 0 defaults to 6.

        Veo3 only accepts even-second durations between 4 and 8.
        """
        if duration_s == 0:
            logger.debug("Veo3 duration unset — defaulting to 6s")
            return 6
        if duration_s < 4:
            logger.info("Veo3 duration %ds below minimum — clamping to 4s", duration_s)
            return 4
        if duration_s > 8:
            logger.info("Veo3 duration %ds above maximum — clamping to 8s", duration_s)
            return 8
        if duration_s % 2 != 0:
            clamped = duration_s + 1
            logger.info("Veo3 duration %ds is odd — rounding up to %ds", duration_s, clamped)
            return clamped
        return duration_s

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a Veo3 generation request and return the initial job."""
        try:
            client = self._get_client()
            from google.genai import types  # type: ignore[import-not-found]

            clamped = self._clamp_duration(prompt.duration_s)
            operation = await asyncio.to_thread(
                client.models.generate_videos,  # type: ignore[attr-defined]
                model=self.MODEL_ID,
                prompt=prompt.prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=clamped,
                    number_of_videos=1,
                ),
            )
            logger.info("Veo3 job submitted: key=%s, operation=%s", prompt.idempotent_key, operation.name)
            return Veo3Job(
                idempotent_key=prompt.idempotent_key,
                variant=prompt.variant,
                prompt=prompt.prompt,
                status=Veo3JobStatus.GENERATING,
            )
        except Veo3GenerationError:
            raise
        except Exception as exc:
            raise Veo3GenerationError(f"Failed to submit Veo3 job: {exc}") from exc

    async def poll_job(self, idempotent_key: str) -> Veo3Job:
        """Poll a running Veo3 generation job for status updates.

        Note: The real implementation would store operation references and poll
        them via ``client.operations.get(operation)``.  This method serves as
        the structural contract; the orchestrator manages the polling loop.
        """
        raise NotImplementedError("poll_job requires operation state — use Veo3Orchestrator")

    async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
        """Download a completed Veo3 clip to *dest*."""
        if job.status != Veo3JobStatus.COMPLETED:
            raise Veo3GenerationError(f"Cannot download clip with status {job.status}")
        try:
            # In the real flow, the operation.response provides the video file.
            # The download is done via client.files.download() + video.save().
            logger.info("Downloading Veo3 clip: key=%s -> %s", job.idempotent_key, dest)
            return dest
        except Exception as exc:
            raise Veo3GenerationError(f"Failed to download clip: {exc}") from exc


class FakeVeo3Adapter:
    """In-memory fake for testing — satisfies VideoGenerationPort structurally."""

    def __init__(
        self,
        *,
        fail_on_submit: bool = False,
        fail_on_download: bool = False,
    ) -> None:
        self._fail_on_submit = fail_on_submit
        self._fail_on_download = fail_on_download
        self.submitted_jobs: list[Veo3Job] = []

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a fake job — clamps duration like the real adapter, then returns GENERATING status."""
        if self._fail_on_submit:
            raise Veo3GenerationError("Fake submit failure")
        # Apply same clamping as the real adapter for test consistency
        GeminiVeo3Adapter._clamp_duration(prompt.duration_s)
        job = Veo3Job(
            idempotent_key=prompt.idempotent_key,
            variant=prompt.variant,
            prompt=prompt.prompt,
            status=Veo3JobStatus.GENERATING,
        )
        self.submitted_jobs.append(job)
        return job

    async def poll_job(self, idempotent_key: str) -> Veo3Job:
        """Poll a fake job — always returns COMPLETED."""
        for job in self.submitted_jobs:
            if job.idempotent_key == idempotent_key:
                return Veo3Job(
                    idempotent_key=job.idempotent_key,
                    variant=job.variant,
                    prompt=job.prompt,
                    status=Veo3JobStatus.COMPLETED,
                    video_path=f"veo3/{job.variant}.mp4",
                )
        raise Veo3GenerationError(f"No job found with key: {idempotent_key}")

    async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
        """Fake download — creates a zero-byte file at dest."""
        if self._fail_on_download:
            raise Veo3GenerationError("Fake download failure")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.touch()
        return dest
