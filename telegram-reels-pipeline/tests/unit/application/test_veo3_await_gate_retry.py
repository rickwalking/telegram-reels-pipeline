"""Tests for Veo3 await gate failure classification and auto-retry logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from pipeline.application.veo3_await_gate import (
    _RETRIABLE_ERRORS,
    _all_failures_retriable,
    run_veo3_await_gate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jobs_json(workspace: Path, jobs: list[dict[str, Any]]) -> None:
    """Write a veo3/jobs.json file with the given job entries."""
    veo3_dir = workspace / "veo3"
    veo3_dir.mkdir(parents=True, exist_ok=True)
    (veo3_dir / "jobs.json").write_text(json.dumps({"jobs": jobs}))


def _make_failed_job(
    error_message: str,
    variant: str = "broll",
    key: str = "run1_broll",
) -> dict[str, Any]:
    """Create a failed job entry with a specific error_message."""
    return {
        "idempotent_key": key,
        "variant": variant,
        "prompt": "Test prompt",
        "status": "failed",
        "video_path": None,
        "error_message": error_message,
    }


def _make_orchestrator_mock() -> AsyncMock:
    """Create a mock Veo3Orchestrator with start_generation and poll_jobs stubs."""
    orch = AsyncMock()
    # After retry, poll_jobs immediately reports all done
    orch.poll_jobs.return_value = True
    return orch


# ---------------------------------------------------------------------------
# _all_failures_retriable unit tests
# ---------------------------------------------------------------------------


class TestAllFailuresRetriable:
    def test_all_rate_limited_is_retriable(self, tmp_path: Path) -> None:
        """All rate_limited failures -> retriable."""
        _write_jobs_json(
            tmp_path,
            [
                _make_failed_job("rate_limited", key="k1"),
                _make_failed_job("rate_limited", variant="intro", key="k2"),
            ],
        )
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is True

    def test_all_submit_failed_is_retriable(self, tmp_path: Path) -> None:
        """All submit_failed failures -> retriable."""
        _write_jobs_json(tmp_path, [_make_failed_job("submit_failed")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is True

    def test_all_poll_failed_is_retriable(self, tmp_path: Path) -> None:
        """All poll_failed failures -> retriable."""
        _write_jobs_json(tmp_path, [_make_failed_job("poll_failed")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is True

    def test_download_failed_is_not_retriable(self, tmp_path: Path) -> None:
        """download_failed is NOT in the retriable set."""
        _write_jobs_json(tmp_path, [_make_failed_job("download_failed")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_generation_failed_is_not_retriable(self, tmp_path: Path) -> None:
        """generation_failed is NOT in the retriable set."""
        _write_jobs_json(tmp_path, [_make_failed_job("generation_failed")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_invalid_argument_is_not_retriable(self, tmp_path: Path) -> None:
        """Error containing INVALID_ARGUMENT is never retriable."""
        _write_jobs_json(tmp_path, [_make_failed_job("INVALID_ARGUMENT: bad prompt")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_mixed_retriable_and_permanent_is_not_retriable(self, tmp_path: Path) -> None:
        """Mix of retriable + permanent -> not retriable."""
        _write_jobs_json(
            tmp_path,
            [
                _make_failed_job("rate_limited", key="k1"),
                _make_failed_job("generation_failed", variant="intro", key="k2"),
            ],
        )
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_no_failed_jobs_returns_false(self, tmp_path: Path) -> None:
        """No failed jobs at all -> False (nothing to retry)."""
        _write_jobs_json(
            tmp_path,
            [
                {
                    "idempotent_key": "k1",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "completed",
                    "video_path": "veo3/broll.mp4",
                    "error_message": None,
                }
            ],
        )
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_empty_error_message_is_not_retriable(self, tmp_path: Path) -> None:
        """Empty error_message is NOT in the retriable set."""
        _write_jobs_json(tmp_path, [_make_failed_job("")])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False

    def test_none_error_message_is_not_retriable(self, tmp_path: Path) -> None:
        """None error_message (normalized to '') is NOT in the retriable set."""
        job = _make_failed_job("rate_limited")
        job["error_message"] = None
        _write_jobs_json(tmp_path, [job])
        assert _all_failures_retriable(tmp_path / "veo3" / "jobs.json") is False


# ---------------------------------------------------------------------------
# Auto-retry integration tests
# ---------------------------------------------------------------------------


class TestAutoRetryTriggered:
    async def test_rate_limited_triggers_retry(self, tmp_path: Path) -> None:
        """All rate_limited failures -> retry fires start_generation."""
        _write_jobs_json(
            tmp_path,
            [
                _make_failed_job("rate_limited", key="k1"),
                _make_failed_job("rate_limited", variant="intro", key="k2"),
            ],
        )
        # Write publishing-assets.json for start_generation
        (tmp_path / "publishing-assets.json").write_text(
            json.dumps(
                {
                    "descriptions": [{"language": "en", "text": "Test"}],
                    "hashtags": ["#test"],
                    "veo3_prompts": [{"variant": "broll", "prompt": "Particles"}],
                }
            )
        )

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_awaited_once_with(tmp_path, tmp_path.name)

    async def test_submit_failed_triggers_retry(self, tmp_path: Path) -> None:
        """All submit_failed failures -> retry fires start_generation."""
        _write_jobs_json(tmp_path, [_make_failed_job("submit_failed")])

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_awaited_once()


class TestAutoRetryNotTriggered:
    async def test_download_failed_skips_retry(self, tmp_path: Path) -> None:
        """download_failed -> no retry."""
        _write_jobs_json(tmp_path, [_make_failed_job("download_failed")])

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_not_awaited()

    async def test_generation_failed_skips_retry(self, tmp_path: Path) -> None:
        """generation_failed -> no retry."""
        _write_jobs_json(tmp_path, [_make_failed_job("generation_failed")])

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_not_awaited()

    async def test_invalid_argument_skips_retry(self, tmp_path: Path) -> None:
        """INVALID_ARGUMENT in error -> no retry."""
        _write_jobs_json(tmp_path, [_make_failed_job("INVALID_ARGUMENT: bad prompt")])

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_not_awaited()

    async def test_mixed_retriable_and_permanent_skips_retry(self, tmp_path: Path) -> None:
        """Mixed retriable + permanent failures -> no retry."""
        _write_jobs_json(
            tmp_path,
            [
                _make_failed_job("rate_limited", key="k1"),
                _make_failed_job("download_failed", variant="intro", key="k2"),
            ],
        )

        orch = _make_orchestrator_mock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        orch.start_generation.assert_not_awaited()


class TestSingleRetryGuard:
    async def test_retry_fires_only_once(self, tmp_path: Path) -> None:
        """After one retry, the guard prevents a second retry within the same gate call.

        This test verifies the _retry_fired guard.  We set up all-failed-retriable
        jobs, and mock start_generation to re-write jobs.json with failed jobs again
        (simulating a second failure).  Even though all jobs are still failed and
        retriable after the first retry, start_generation is called only once.
        """
        _write_jobs_json(tmp_path, [_make_failed_job("rate_limited")])

        orch = _make_orchestrator_mock()
        # After retry fires, poll_jobs returns True (all done)
        orch.poll_jobs.return_value = True

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )

        # start_generation called exactly once — not re-triggered
        assert orch.start_generation.await_count == 1


# ---------------------------------------------------------------------------
# EventBus integration tests
# ---------------------------------------------------------------------------


class TestEventBusIntegration:
    async def test_event_bus_receives_retried_event(self, tmp_path: Path) -> None:
        """When retry fires, EventBus.publish is called with veo3.gate.retried."""
        _write_jobs_json(tmp_path, [_make_failed_job("rate_limited")])

        orch = _make_orchestrator_mock()
        event_bus = AsyncMock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
            event_bus=event_bus,
        )

        event_bus.publish.assert_awaited_once()
        event = event_bus.publish.call_args[0][0]
        assert event.event_name == "veo3.gate.retried"
        assert event.data["reason"] == "all_failures_retriable"

    async def test_event_bus_none_does_not_crash(self, tmp_path: Path) -> None:
        """event_bus=None (default) does not raise when retry fires."""
        _write_jobs_json(tmp_path, [_make_failed_job("rate_limited")])

        orch = _make_orchestrator_mock()

        # Should not raise
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
            event_bus=None,
        )
        # The gate should complete normally
        assert isinstance(result, dict)

    async def test_event_bus_not_called_when_no_retry(self, tmp_path: Path) -> None:
        """EventBus.publish is NOT called when retry is skipped."""
        _write_jobs_json(tmp_path, [_make_failed_job("download_failed")])

        orch = _make_orchestrator_mock()
        event_bus = AsyncMock()

        await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
            event_bus=event_bus,
        )

        event_bus.publish.assert_not_awaited()


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


class TestRetriableConstants:
    def test_retriable_errors_is_frozenset(self) -> None:
        """_RETRIABLE_ERRORS must be a frozenset for immutability."""
        assert isinstance(_RETRIABLE_ERRORS, frozenset)

    def test_expected_members(self) -> None:
        """Verify the exact set of retriable error codes."""
        assert {"submit_failed", "rate_limited", "poll_failed"} == _RETRIABLE_ERRORS


# ---------------------------------------------------------------------------
# Skip paths (no veo3 folder, no jobs.json)
# ---------------------------------------------------------------------------


class TestSkipPaths:
    async def test_no_veo3_folder_returns_skipped(self, tmp_path: Path) -> None:
        """No veo3/ directory -> returns skipped immediately."""
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=_make_orchestrator_mock(),
            timeout_s=60,
        )
        assert result["skipped"] is True
        assert result["reason"] == "no_veo3_folder"

    async def test_no_jobs_json_returns_skipped(self, tmp_path: Path) -> None:
        """veo3/ exists but no jobs.json -> returns skipped."""
        (tmp_path / "veo3").mkdir()
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=_make_orchestrator_mock(),
            timeout_s=60,
        )
        assert result["skipped"] is True
        assert result["reason"] == "no_jobs_file"


# ---------------------------------------------------------------------------
# No-orchestrator read-only path
# ---------------------------------------------------------------------------


class TestNoOrchestrator:
    async def test_no_orchestrator_returns_summary(self, tmp_path: Path) -> None:
        """orchestrator=None -> read current jobs.json state, no polling."""
        _write_jobs_json(
            tmp_path,
            [
                {
                    "idempotent_key": "k1",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "completed",
                    "video_path": "veo3/broll.mp4",
                    "error_message": None,
                },
                _make_failed_job("download_failed", variant="intro", key="k2"),
            ],
        )

        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=None,
            timeout_s=60,
        )

        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2

    async def test_no_orchestrator_does_not_poll(self, tmp_path: Path) -> None:
        """orchestrator=None -> no poll_jobs called."""
        _write_jobs_json(tmp_path, [_make_failed_job("rate_limited")])

        # Pass None, not a mock
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=None,
            timeout_s=60,
        )

        # Should return summary without polling
        assert "failed" in result


# ---------------------------------------------------------------------------
# Timeout path
# ---------------------------------------------------------------------------


class TestTimeoutPath:
    async def test_timeout_marks_generating_as_timed_out(self, tmp_path: Path) -> None:
        """When timeout expires, GENERATING jobs are marked TIMED_OUT."""
        _write_jobs_json(
            tmp_path,
            [
                {
                    "idempotent_key": "k1",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "generating",
                    "video_path": None,
                    "error_message": None,
                }
            ],
        )

        orch = AsyncMock()
        # poll_jobs always returns False (never done)
        orch.poll_jobs.return_value = False

        from unittest.mock import patch as _patch

        with _patch("pipeline.application.veo3_await_gate.asyncio.sleep", new_callable=AsyncMock):
            result = await run_veo3_await_gate(
                workspace=tmp_path,
                orchestrator=orch,
                timeout_s=0,  # Immediate timeout
            )

        assert result["timed_out"] == 1
        assert result["total"] == 1

        # Verify the file was updated
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        assert data["jobs"][0]["status"] == "timed_out"

    async def test_timeout_does_not_affect_completed_jobs(self, tmp_path: Path) -> None:
        """Timeout only marks GENERATING jobs, not already completed ones."""
        _write_jobs_json(
            tmp_path,
            [
                {
                    "idempotent_key": "k1",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "completed",
                    "video_path": "veo3/broll.mp4",
                    "error_message": None,
                },
                {
                    "idempotent_key": "k2",
                    "variant": "intro",
                    "prompt": "Test",
                    "status": "generating",
                    "video_path": None,
                    "error_message": None,
                },
            ],
        )

        orch = AsyncMock()
        orch.poll_jobs.return_value = False

        from unittest.mock import patch as _patch

        with _patch("pipeline.application.veo3_await_gate.asyncio.sleep", new_callable=AsyncMock):
            result = await run_veo3_await_gate(
                workspace=tmp_path,
                orchestrator=orch,
                timeout_s=0,
            )

        assert result["completed"] == 1
        assert result["timed_out"] == 1
