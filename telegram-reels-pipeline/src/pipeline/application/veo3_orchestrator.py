"""Veo3 generation orchestrator — fire parallel async generation after CONTENT stage."""

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
    """Fire parallel Veo3 generation jobs and poll until all complete or timeout.

    Designed to run as a background ``asyncio.Task`` so the main pipeline
    continues through later stages while clips generate.
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
        ``veo3_prompts`` array, caps at *clip_count*, fires all jobs in
        parallel via the adapter's ``submit_job()``, and writes the initial
        ``veo3/jobs.json`` with atomic writes.

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

        # Submit all jobs in parallel
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

    async def _submit_all(self, prompts: list[Veo3Prompt]) -> list[Veo3Job]:
        """Submit every prompt concurrently via asyncio.gather()."""

        async def _submit_one(prompt: Veo3Prompt) -> Veo3Job:
            try:
                result = await self._video_gen.submit_job(prompt)
                logger.info("Veo3 job submitted: key=%s", prompt.idempotent_key)
                return result
            except Exception:
                logger.exception("Veo3 submit failed for %s", prompt.idempotent_key)
                return Veo3Job(
                    idempotent_key=prompt.idempotent_key,
                    variant=prompt.variant,
                    prompt=prompt.prompt,
                    status=Veo3JobStatus.FAILED,
                    error_message="submit_failed",
                )

        results = await asyncio.gather(*(_submit_one(p) for p in prompts))
        return list(results)

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
