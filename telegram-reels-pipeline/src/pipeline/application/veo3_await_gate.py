"""Veo3 await gate -- block before Assembly until all Veo3 jobs resolve."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pipeline.application.event_bus import EventBus
    from pipeline.application.veo3_orchestrator import Veo3Orchestrator

logger = logging.getLogger(__name__)

# Polling backoff parameters
_INITIAL_POLL_S = 5
_MAX_POLL_S = 30

# Failure error_message values that are safe to auto-retry
_RETRIABLE_ERRORS = frozenset({"submit_failed", "rate_limited", "poll_failed"})


async def run_veo3_await_gate(
    workspace: Path,
    orchestrator: Veo3Orchestrator | None,
    timeout_s: int,
    event_bus: EventBus | None = None,
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
        event_bus: Optional EventBus for emitting retry events.
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

    # Auto-retry: if all jobs failed AND every failure is retriable,
    # re-submit them once before entering the polling loop.
    _retry_fired = False
    if await asyncio.to_thread(_all_jobs_failed, jobs_path):
        if await asyncio.to_thread(_all_failures_retriable, jobs_path):
            run_id = workspace.name
            logger.info("All Veo3 jobs failed with retriable errors — retrying submission for run %s", run_id)
            await orchestrator.start_generation(workspace, run_id)
            _retry_fired = True

            if event_bus is not None:
                from pipeline.domain.models import PipelineEvent

                await event_bus.publish(
                    PipelineEvent(
                        timestamp=datetime.now(UTC).isoformat(),
                        event_name="veo3.gate.retried",
                        data=MappingProxyType({"reason": "all_failures_retriable"}),
                    )
                )
        else:
            logger.warning("All Veo3 jobs failed with permanent errors — skipping retry")

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


def _all_failures_retriable(jobs_path: Path) -> bool:
    """Return True only if every failed job has a retriable error_message.

    A failure is retriable when its ``error_message`` is in
    ``_RETRIABLE_ERRORS`` *and* does not contain ``INVALID_ARGUMENT``.
    """
    try:
        data = json.loads(jobs_path.read_text())
    except (json.JSONDecodeError, OSError):
        return False

    failed_jobs = [j for j in data.get("jobs", []) if j.get("status") == "failed"]
    if not failed_jobs:
        return False

    for job in failed_jobs:
        error_msg = job.get("error_message", "") or ""
        if "INVALID_ARGUMENT" in error_msg:
            return False
        if error_msg not in _RETRIABLE_ERRORS:
            return False

    return True


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
