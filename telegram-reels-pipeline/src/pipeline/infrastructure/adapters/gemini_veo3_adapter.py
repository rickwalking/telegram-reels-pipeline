"""Gemini Veo3 adapter — implements VideoGenerationPort via google-genai SDK."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile
import urllib.request
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
                raise Veo3GenerationError("google-genai SDK not installed — run: poetry add google-genai") from exc
        return self._client

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a Veo3 generation request and return the initial job."""
        try:
            client = self._get_client()
            from google.genai import types  # type: ignore[import-not-found]

            operation = await asyncio.to_thread(
                client.models.generate_videos,  # type: ignore[attr-defined]
                model=self.MODEL_ID,
                prompt=prompt.prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=str(prompt.duration_s) if prompt.duration_s else "6",
                    number_of_videos=1,
                ),
            )
            op_name = str(operation.name) if operation.name else ""
            logger.info("Veo3 job submitted: key=%s, operation=%s", prompt.idempotent_key, op_name)
            return Veo3Job(
                idempotent_key=prompt.idempotent_key,
                variant=prompt.variant,
                prompt=prompt.prompt,
                status=Veo3JobStatus.GENERATING,
                operation_name=op_name,
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
        """Download a completed Veo3 clip to *dest* via operation polling + authenticated HTTP."""
        if job.status != Veo3JobStatus.COMPLETED:
            raise Veo3GenerationError(f"Cannot download clip with status {job.status}")
        if not job.operation_name:
            raise Veo3GenerationError("Cannot download clip without operation_name")
        try:
            from google.genai import types  # noqa: F811

            client = self._get_client()
            op_ref = types.GenerateVideosOperation(name=job.operation_name)
            operation = await asyncio.to_thread(
                client.operations.get,  # type: ignore[attr-defined]
                operation=op_ref,
            )
            video_uri: str = operation.result.generated_videos[0].video.uri
            logger.info("Downloading Veo3 clip: key=%s, uri=%s -> %s", job.idempotent_key, video_uri, dest)

            req = urllib.request.Request(video_uri, headers={"x-goog-api-key": self._api_key})
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=str(dest.parent), suffix=".tmp")
            try:
                response = await asyncio.to_thread(urllib.request.urlopen, req)
                with os.fdopen(fd, "wb") as f:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                os.rename(tmp_path, str(dest))
            except BaseException:
                with contextlib.suppress(OSError):
                    os.unlink(tmp_path)
                raise

            return dest
        except Veo3GenerationError:
            raise
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
        """Submit a fake job — immediately returns GENERATING status."""
        if self._fail_on_submit:
            raise Veo3GenerationError("Fake submit failure")
        job = Veo3Job(
            idempotent_key=prompt.idempotent_key,
            variant=prompt.variant,
            prompt=prompt.prompt,
            status=Veo3JobStatus.GENERATING,
            operation_name=f"operations/fake-op-{prompt.variant}",
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
                    operation_name=job.operation_name,
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
