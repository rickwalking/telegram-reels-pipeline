"""Veo3 await gate -- block before Assembly until all Veo3 jobs resolve."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.application.veo3_orchestrator import Veo3Orchestrator

logger = logging.getLogger(__name__)

# Polling backoff parameters
_INITIAL_POLL_S = 5
_MAX_POLL_S = 30


async def run_veo3_await_gate(
    workspace: Path,
    orchestrator: Veo3Orchestrator | None,
    timeout_s: int,
) -> dict[str, Any]:
    """Block until all Veo3 jobs reach a terminal state or timeout.

    Returns a summary dict with counts of completed, failed, timed_out, and
    total jobs.  Returns immediately with ``skipped=True`` if no Veo3 work
    is present.

    Args:
        workspace: Run workspace directory.
        orchestrator: Optional Veo3Orchestrator for polling. When ``None``,
            the gate checks files only and cannot poll.
        timeout_s: Maximum seconds to wait before marking remaining jobs
            as timed-out.
    """
    veo3_dir = workspace / "veo3"
    if not await asyncio.to_thread(veo3_dir.exists):
        logger.debug("No veo3/ folder -- skipping await gate")
        return {"skipped": True, "reason": "no_veo3_folder"}

    jobs_path = veo3_dir / "jobs.json"
    if not await asyncio.to_thread(jobs_path.exists):
        logger.debug("No veo3/jobs.json -- skipping await gate")
        return {"skipped": True, "reason": "no_jobs_file"}

    # If no orchestrator, we cannot poll -- just read current state
    if orchestrator is None:
        summary = await asyncio.to_thread(_read_summary, jobs_path)
        logger.info("Veo3 await gate (no orchestrator): %s", summary)
        return summary

    # Auto-retry: if all jobs failed (e.g. missing SDK, transient API error),
    # re-submit them before entering the polling loop.
    if await asyncio.to_thread(_all_jobs_failed, jobs_path):
        run_id = workspace.name
        logger.info("All Veo3 jobs failed — retrying submission for run %s", run_id)
        await orchestrator.start_generation(workspace, run_id)

    # Polling loop with exponential backoff
    poll_interval = _INITIAL_POLL_S
    elapsed = 0.0

    while elapsed < timeout_s:
        all_done = await orchestrator.poll_jobs(workspace)
        if all_done:
            break

        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        # Exponential backoff, capped at _MAX_POLL_S
        poll_interval = min(poll_interval * 2, _MAX_POLL_S)

    # If timed out, mark remaining GENERATING jobs as TIMED_OUT
    if elapsed >= timeout_s:
        logger.warning("Veo3 await gate timed out after %ds", timeout_s)
        await asyncio.to_thread(_mark_timed_out, jobs_path)

    summary = await asyncio.to_thread(_read_summary, jobs_path)
    return summary


def _all_jobs_failed(jobs_path: Path) -> bool:
    """Return True if jobs.json exists and every job has status 'failed'."""
    try:
        data = json.loads(jobs_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    jobs = data.get("jobs", [])
    return bool(jobs) and all(j.get("status") == "failed" for j in jobs)


def _read_summary(jobs_path: Path) -> dict[str, Any]:
    """Read jobs.json and return a summary dict."""
    try:
        data = json.loads(jobs_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"completed": 0, "failed": 0, "timed_out": 0, "total": 0}

    jobs = data.get("jobs", [])
    completed = sum(1 for j in jobs if j.get("status") == "completed")
    failed = sum(1 for j in jobs if j.get("status") == "failed")
    timed_out = sum(1 for j in jobs if j.get("status") == "timed_out")
    return {
        "completed": completed,
        "failed": failed,
        "timed_out": timed_out,
        "total": len(jobs),
    }


def _mark_timed_out(jobs_path: Path) -> None:
    """Mark any GENERATING jobs as TIMED_OUT in jobs.json (atomic write)."""
    import os
    import tempfile

    try:
        data = json.loads(jobs_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    changed = False
    for job in data.get("jobs", []):
        if job.get("status") == "generating":
            job["status"] = "timed_out"
            changed = True

    if not changed:
        return

    parent = jobs_path.parent
    fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.rename(tmp_path, str(jobs_path))
    except BaseException:
        import contextlib

        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
