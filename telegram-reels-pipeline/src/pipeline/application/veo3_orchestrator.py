"""Veo3 generation orchestrator — sequential submission with rate-limit retry."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt, make_idempotent_key

if TYPE_CHECKING:
    from pipeline.domain.ports import VideoGenerationPort

logger = logging.getLogger(__name__)

# Terminal states — no further polling needed.
_TERMINAL_STATUSES = frozenset({Veo3JobStatus.COMPLETED, Veo3JobStatus.FAILED, Veo3JobStatus.TIMED_OUT})


class Veo3Orchestrator:
    """Fire sequential Veo3 generation jobs and poll until all complete or timeout.

    Jobs are submitted one at a time with inter-submission delays and
    exponential backoff on rate-limit errors.  Designed to run as a
    background ``asyncio.Task`` so the main pipeline continues through
    later stages while clips generate.
    """

    def __init__(
        self,
        video_gen: VideoGenerationPort,
        clip_count: int,
        timeout_s: int,
    ) -> None:
        self._video_gen = video_gen
        self._clip_count = clip_count
        self._timeout_s = timeout_s

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start_generation(self, workspace: Path, run_id: str) -> None:
        """Kick off Veo3 generation for prompts found in publishing-assets.json.

        Reads ``publishing-assets.json`` from *workspace*, extracts the
        ``veo3_prompts`` array, caps at *clip_count*, submits jobs
        sequentially via the adapter's ``submit_job()`` with rate-limit
        retry, and writes the initial ``veo3/jobs.json`` with atomic writes.

        If the prompts array is empty or missing, returns early (no-op,
        no ``veo3/`` folder created).
        """
        prompts_raw = await self._read_prompts(workspace)
        if not prompts_raw:
            logger.debug("No Veo3 prompts \u2014 skipping generation")
            return

        capped = prompts_raw[: self._clip_count]
        veo3_dir = workspace / "veo3"
        await asyncio.to_thread(veo3_dir.mkdir, parents=True, exist_ok=True)

        veo3_prompts = self._convert_prompts(capped, run_id)

        # Submit jobs sequentially with rate-limit retry
        submitted = await self._submit_all(veo3_prompts)

        # Write initial jobs.json atomically
        jobs_path = veo3_dir / "jobs.json"
        await asyncio.to_thread(self._write_jobs_json, jobs_path, submitted)

    async def poll_jobs(self, workspace: Path) -> bool:
        """Poll active Veo3 jobs and update ``veo3/jobs.json``.

        Reads ``veo3/jobs.json``, polls each job still in GENERATING status
        via the adapter's ``poll_job()``, and atomically updates the file.
        Independent per-clip tracking: if one job fails, others continue.

        Returns:
            ``True`` if all jobs have reached a terminal state
            (completed / failed / timed_out), ``False`` otherwise.
        """
        jobs_path = workspace / "veo3" / "jobs.json"
        jobs = await asyncio.to_thread(self._read_jobs_json, jobs_path)
        if not jobs:
            return True

        changed = False
        for i, job in enumerate(jobs):
            if job.status not in _TERMINAL_STATUSES:
                try:
                    updated = await self._video_gen.poll_job(job.idempotent_key)
                    if updated.status != job.status:
                        changed = True
                    jobs[i] = updated
                except Exception:
                    logger.exception("Poll failed for %s", job.idempotent_key)
                    jobs[i] = Veo3Job(
                        idempotent_key=job.idempotent_key,
                        variant=job.variant,
                        prompt=job.prompt,
                        status=Veo3JobStatus.FAILED,
                        error_message="poll_failed",
                    )
                    changed = True

        if changed:
            await asyncio.to_thread(self._write_jobs_json, jobs_path, jobs)

        return all(j.status in _TERMINAL_STATUSES for j in jobs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _read_prompts(workspace: Path) -> list[dict[str, object]]:
        """Read veo3_prompts from publishing-assets.json, returning [] on any failure."""
        assets_path = workspace / "publishing-assets.json"
        try:
            raw = await asyncio.to_thread(assets_path.read_text)
            data = json.loads(raw)
            prompts = data.get("veo3_prompts", [])
            if not isinstance(prompts, list):
                return []
            return prompts
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            logger.debug("Cannot read publishing-assets.json: %s", exc)
            return []

    @staticmethod
    def _convert_prompts(raw: list[dict[str, object]], run_id: str) -> list[Veo3Prompt]:
        """Convert raw prompt dicts into ``Veo3Prompt`` dataclass instances."""
        result: list[Veo3Prompt] = []
        for d in raw:
            variant = str(d.get("variant", ""))
            prompt_text = str(d.get("prompt", ""))
            narrative_anchor = str(d.get("narrative_anchor", ""))
            raw_duration = d.get("duration_s", 0) or 0
            duration_s = int(str(raw_duration))
            key = make_idempotent_key(run_id, variant)
            result.append(
                Veo3Prompt(
                    variant=variant,
                    prompt=prompt_text,
                    narrative_anchor=narrative_anchor,
                    duration_s=duration_s,
                    idempotent_key=key,
                )
            )
        return result

    # Patterns that indicate a retryable rate-limit / server error.
    _RETRYABLE_PATTERNS: tuple[str, ...] = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")
    # Patterns that indicate a permanent client error — never retry.
    _PERMANENT_PATTERNS: tuple[str, ...] = ("400", "INVALID_ARGUMENT")
    _MAX_RETRIES: int = 3
    _BACKOFF_DELAYS: tuple[int, ...] = (30, 60, 120)
    _INTER_SUBMIT_DELAY: int = 5

    async def _submit_all(self, prompts: list[Veo3Prompt]) -> list[Veo3Job]:
        """Submit prompts sequentially with a delay between each to avoid rate limits."""
        results: list[Veo3Job] = []
        for idx, prompt in enumerate(prompts):
            job = await self._submit_with_retry(prompt)
            results.append(job)
            # Sleep between submissions (but not after the last one)
            if idx < len(prompts) - 1:
                await asyncio.sleep(self._INTER_SUBMIT_DELAY)
        return results

    async def _submit_with_retry(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a single job with exponential backoff on retryable errors.

        Retries up to ``_MAX_RETRIES`` times for rate-limit / server errors
        (429, RESOURCE_EXHAUSTED, 503, UNAVAILABLE).  Client errors (400,
        INVALID_ARGUMENT) fail immediately without retry.
        """
        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                result = await self._video_gen.submit_job(prompt)
                logger.info("Veo3 job submitted: key=%s", prompt.idempotent_key)
                return result
            except Exception as exc:
                error_str = str(exc)
                if self._is_retryable(error_str) and attempt < self._MAX_RETRIES:
                    delay = self._BACKOFF_DELAYS[attempt - 1]
                    logger.warning(
                        "Veo3 submit retry %d/%d for %s, waiting %ds",
                        attempt,
                        self._MAX_RETRIES,
                        prompt.variant,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue
                if self._is_retryable(error_str):
                    # Final retry exhausted
                    logger.error("Veo3 submit exhausted retries for %s: %s", prompt.variant, error_str)
                    return Veo3Job(
                        idempotent_key=prompt.idempotent_key,
                        variant=prompt.variant,
                        prompt=prompt.prompt,
                        status=Veo3JobStatus.FAILED,
                        error_message="rate_limited",
                    )
                # Permanent failure — do not retry
                logger.error("Veo3 submit permanent failure for %s: %s", prompt.variant, error_str)
                return Veo3Job(
                    idempotent_key=prompt.idempotent_key,
                    variant=prompt.variant,
                    prompt=prompt.prompt,
                    status=Veo3JobStatus.FAILED,
                    error_message=error_str,
                )
        # Unreachable, but satisfies type checker
        return Veo3Job(  # pragma: no cover
            idempotent_key=prompt.idempotent_key,
            variant=prompt.variant,
            prompt=prompt.prompt,
            status=Veo3JobStatus.FAILED,
            error_message="rate_limited",
        )

    @staticmethod
    def _is_retryable(error_msg: str) -> bool:
        """Return True if the error message indicates a retryable server/rate-limit error."""
        return any(pattern in error_msg for pattern in Veo3Orchestrator._RETRYABLE_PATTERNS)

    @staticmethod
    def _write_jobs_json(jobs_path: Path, jobs: list[Veo3Job]) -> None:
        """Atomic write: write to tempfile in same directory, then os.rename()."""
        data = {
            "jobs": [
                {
                    "idempotent_key": j.idempotent_key,
                    "variant": j.variant,
                    "prompt": j.prompt,
                    "status": j.status.value,
                    "operation_name": j.operation_name,
                    "video_path": j.video_path,
                    "error_message": j.error_message,
                }
                for j in jobs
            ]
        }
        parent = jobs_path.parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.rename(tmp_path, str(jobs_path))
        except BaseException:
            # Clean up temp file on failure
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    @staticmethod
    def _read_jobs_json(jobs_path: Path) -> list[Veo3Job]:
        """Read ``veo3/jobs.json`` and return Veo3Job instances."""
        try:
            raw = jobs_path.read_text()
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

        jobs: list[Veo3Job] = []
        for entry in data.get("jobs", []):
            try:
                jobs.append(
                    Veo3Job(
                        idempotent_key=entry["idempotent_key"],
                        variant=entry["variant"],
                        prompt=entry["prompt"],
                        status=Veo3JobStatus(entry["status"]),
                        operation_name=entry.get("operation_name", ""),
                        video_path=entry.get("video_path"),
                        error_message=entry.get("error_message"),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed job entry: %s", exc)
        return jobs
