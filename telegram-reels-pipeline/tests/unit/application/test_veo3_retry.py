"""Tests for Veo3 sequential submission and exponential backoff retry logic."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

from pipeline.application.veo3_orchestrator import Veo3Orchestrator
from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt
from pipeline.infrastructure.adapters.gemini_veo3_adapter import Veo3GenerationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_publishing_assets(workspace: Path, prompts: list[dict[str, object]]) -> None:
    """Write a publishing-assets.json file with the given veo3_prompts."""
    assets = {
        "descriptions": [{"language": "en", "text": "Test description"}],
        "hashtags": ["#test"],
        "veo3_prompts": prompts,
    }
    (workspace / "publishing-assets.json").write_text(json.dumps(assets))


def _prompt_dict(**overrides: Any) -> dict[str, object]:
    defaults: dict[str, object] = {
        "variant": "broll",
        "prompt": "Abstract data visualization with flowing particles",
    }
    defaults.update(overrides)
    return defaults


def _make_prompt(variant: str = "broll", prompt: str = "Test prompt", run_id: str = "run-1") -> Veo3Prompt:
    from pipeline.domain.models import make_idempotent_key

    return Veo3Prompt(
        variant=variant,
        prompt=prompt,
        idempotent_key=make_idempotent_key(run_id, variant),
    )


class SequenceTrackingAdapter:
    """Adapter that records the order and timing of submit_job calls.

    Optionally raises errors for specific variants or call counts.
    """

    def __init__(
        self,
        *,
        fail_variants: dict[str, str] | None = None,
        fail_counts: dict[str, int] | None = None,
    ) -> None:
        self.submitted_jobs: list[Veo3Job] = []
        self.call_log: list[str] = []
        # variant -> error message to raise
        self._fail_variants = fail_variants or {}
        # variant -> number of times to fail before succeeding (0 = always succeed)
        self._fail_counts = fail_counts or {}
        self._attempt_counts: dict[str, int] = {}

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        self.call_log.append(prompt.variant)
        variant = prompt.variant

        # Track attempts per variant
        self._attempt_counts[variant] = self._attempt_counts.get(variant, 0) + 1

        if variant in self._fail_variants:
            remaining_fails = self._fail_counts.get(variant, 999)
            if self._attempt_counts[variant] <= remaining_fails:
                raise Veo3GenerationError(self._fail_variants[variant])

        job = Veo3Job(
            idempotent_key=prompt.idempotent_key,
            variant=prompt.variant,
            prompt=prompt.prompt,
            status=Veo3JobStatus.GENERATING,
        )
        self.submitted_jobs.append(job)
        return job

    async def poll_job(self, idempotent_key: str) -> Veo3Job:
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
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.touch()
        return dest


# ---------------------------------------------------------------------------
# TestSequentialSubmission
# ---------------------------------------------------------------------------


class TestSequentialSubmission:
    """Verify that jobs are submitted one at a time, not in parallel."""

    async def test_jobs_submitted_sequentially(self, tmp_path: Path) -> None:
        """All prompts are submitted one at a time in order."""
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompts = [
            _prompt_dict(variant="intro", prompt="Intro sequence"),
            _prompt_dict(variant="broll", prompt="Abstract visualization"),
            _prompt_dict(variant="outro", prompt="Fade to black ending"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            await orch.start_generation(tmp_path, "run-seq")

        # Call log shows sequential order
        assert adapter.call_log == ["intro", "broll", "outro"]
        assert len(adapter.submitted_jobs) == 3

    async def test_inter_submission_delay(self, tmp_path: Path) -> None:
        """A 5s delay is inserted between each submission (not after the last)."""
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompts = [
            _prompt_dict(variant="intro", prompt="Intro"),
            _prompt_dict(variant="broll", prompt="Broll"),
            _prompt_dict(variant="outro", prompt="Outro"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await orch.start_generation(tmp_path, "run-delay")

        # 2 inter-submission delays for 3 prompts (not after last)
        delay_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert delay_calls.count(5) == 2

    async def test_single_prompt_no_inter_delay(self, tmp_path: Path) -> None:
        """A single prompt should not trigger any inter-submission delay."""
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        _write_publishing_assets(tmp_path, [_prompt_dict()])

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await orch.start_generation(tmp_path, "run-single")

        # No inter-submission delay for a single prompt
        delay_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert 5 not in delay_calls


# ---------------------------------------------------------------------------
# TestRetryExponentialBackoff
# ---------------------------------------------------------------------------


class TestRetryExponentialBackoff:
    """Verify exponential backoff on retryable errors (429, 503, etc)."""

    async def test_429_triggers_backoff(self) -> None:
        """A 429 error triggers exponential backoff delays of 30s, 60s, then fails as rate_limited."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "429 Too Many Requests"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert job.error_message == "rate_limited"
        # 3 attempts total: 2 retries with backoff (30s, 60s), 3rd attempt fails and exhausts
        backoff_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert backoff_calls == [30, 60]

    async def test_503_triggers_same_backoff(self) -> None:
        """A 503 error triggers the same exponential backoff as 429."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "503 Service Unavailable"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert job.error_message == "rate_limited"
        backoff_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert backoff_calls == [30, 60]

    async def test_resource_exhausted_triggers_backoff(self) -> None:
        """RESOURCE_EXHAUSTED error string triggers backoff retry."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "RESOURCE_EXHAUSTED: quota limit reached"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert job.error_message == "rate_limited"

    async def test_unavailable_triggers_backoff(self) -> None:
        """UNAVAILABLE error string triggers backoff retry."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "UNAVAILABLE: server overloaded"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert job.error_message == "rate_limited"

    async def test_retry_then_succeed(self) -> None:
        """Succeeds on 2nd attempt after one 429 error (only 30s backoff)."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "429 Too Many Requests"},
            fail_counts={"broll": 1},  # Fail once, then succeed
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.GENERATING
        backoff_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert backoff_calls == [30]


# ---------------------------------------------------------------------------
# TestPermanentFailure
# ---------------------------------------------------------------------------


class TestPermanentFailure:
    """Verify that client errors (400, INVALID_ARGUMENT) fail immediately."""

    async def test_400_fails_immediately(self) -> None:
        """A 400 error fails immediately without any retry."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "400 Bad Request: invalid prompt"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert "400 Bad Request" in (job.error_message or "")
        # No sleep calls — no retry
        assert mock_sleep.call_count == 0

    async def test_invalid_argument_fails_immediately(self) -> None:
        """INVALID_ARGUMENT error fails immediately without retry."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "INVALID_ARGUMENT: prompt too long"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert "INVALID_ARGUMENT" in (job.error_message or "")
        assert mock_sleep.call_count == 0

    async def test_unknown_error_fails_immediately(self) -> None:
        """An unknown error (not matching retryable or permanent patterns) fails immediately."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "ConnectionError: network unreachable"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert "ConnectionError" in (job.error_message or "")
        assert mock_sleep.call_count == 0


# ---------------------------------------------------------------------------
# TestRetryExhaustion
# ---------------------------------------------------------------------------


class TestRetryExhaustion:
    """Verify that after 3 failed retries, job is marked as rate_limited."""

    async def test_three_failures_marks_rate_limited(self) -> None:
        """After 3 consecutive retryable failures, job has error_message='rate_limited'."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "429 Too Many Requests"},
            fail_counts={"broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.FAILED
        assert job.error_message == "rate_limited"
        # Exactly 3 attempts
        assert adapter._attempt_counts["broll"] == 3

    async def test_retry_count_is_per_variant(self) -> None:
        """Retry attempts of 2nd attempt use correct delay (60s not 30s after first used 30s)."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"broll": "429 Too Many Requests"},
            fail_counts={"broll": 2},  # Fails 2 times, succeeds on 3rd
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompt = _make_prompt()

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            job = await orch._submit_with_retry(prompt)

        assert job.status == Veo3JobStatus.GENERATING
        backoff_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert backoff_calls == [30, 60]


# ---------------------------------------------------------------------------
# TestIndependentPerJobRetry
# ---------------------------------------------------------------------------


class TestIndependentPerJobRetry:
    """Verify that one job's retry state does not affect others."""

    async def test_independent_retry_counters(self, tmp_path: Path) -> None:
        """One job failing with rate limit does not affect other jobs' retry counters."""
        adapter = SequenceTrackingAdapter(
            fail_variants={"intro": "429 Too Many Requests"},
            fail_counts={"intro": 999},  # intro always fails
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompts = [
            _prompt_dict(variant="intro", prompt="Intro sequence"),
            _prompt_dict(variant="broll", prompt="Abstract visualization"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            await orch.start_generation(tmp_path, "run-indep")

        # intro failed after 3 retries, broll succeeded on first attempt
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        statuses = {j["variant"]: j["status"] for j in data["jobs"]}
        errors = {j["variant"]: j.get("error_message") for j in data["jobs"]}

        assert statuses["intro"] == "failed"
        assert errors["intro"] == "rate_limited"
        assert statuses["broll"] == "generating"
        assert errors["broll"] is None

    async def test_both_jobs_retry_independently(self, tmp_path: Path) -> None:
        """Two jobs with different error types are handled independently."""
        adapter = SequenceTrackingAdapter(
            fail_variants={
                "intro": "429 Too Many Requests",
                "broll": "400 Bad Request: invalid prompt",
            },
            fail_counts={"intro": 999, "broll": 999},
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompts = [
            _prompt_dict(variant="intro", prompt="Intro"),
            _prompt_dict(variant="broll", prompt="Broll"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        with patch("pipeline.application.veo3_orchestrator.asyncio.sleep", new_callable=AsyncMock):
            await orch.start_generation(tmp_path, "run-both-fail")

        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        errors = {j["variant"]: j.get("error_message") for j in data["jobs"]}

        # intro: retryable -> rate_limited after exhaustion
        assert errors["intro"] == "rate_limited"
        # broll: permanent -> immediate failure with error message
        assert "400 Bad Request" in (errors["broll"] or "")


# ---------------------------------------------------------------------------
# TestIsRetryable
# ---------------------------------------------------------------------------


class TestIsRetryable:
    """Unit tests for the _is_retryable static method."""

    def test_429_is_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("429 Too Many Requests") is True

    def test_503_is_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("503 Service Unavailable") is True

    def test_resource_exhausted_is_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("RESOURCE_EXHAUSTED: quota limit") is True

    def test_unavailable_is_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("UNAVAILABLE: server overloaded") is True

    def test_400_is_not_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("400 Bad Request") is False

    def test_invalid_argument_is_not_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("INVALID_ARGUMENT: bad prompt") is False

    def test_generic_error_is_not_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("ConnectionError: network") is False

    def test_empty_string_is_not_retryable(self) -> None:
        assert Veo3Orchestrator._is_retryable("") is False


# ---------------------------------------------------------------------------
# TestPollJobs
# ---------------------------------------------------------------------------


class TestPollJobs:
    """Tests for poll_jobs() — poll active Veo3 jobs and update jobs.json."""

    @staticmethod
    def _write_jobs_json(workspace: Path, jobs: list[dict[str, Any]]) -> None:
        veo3_dir = workspace / "veo3"
        veo3_dir.mkdir(parents=True, exist_ok=True)
        (veo3_dir / "jobs.json").write_text(json.dumps({"jobs": jobs}))

    @staticmethod
    def _read_jobs(workspace: Path) -> list[dict[str, Any]]:
        return json.loads((workspace / "veo3" / "jobs.json").read_text())["jobs"]

    @staticmethod
    def _generating_job(variant: str = "broll", key: str = "run1_broll") -> dict[str, Any]:
        return {
            "idempotent_key": key,
            "variant": variant,
            "prompt": "Test prompt",
            "status": "generating",
            "operation_name": "",
            "video_path": None,
            "error_message": None,
        }

    @staticmethod
    def _completed_job(variant: str = "broll", key: str = "run1_broll") -> dict[str, Any]:
        return {
            "idempotent_key": key,
            "variant": variant,
            "prompt": "Test prompt",
            "status": "completed",
            "operation_name": "",
            "video_path": f"veo3/{variant}.mp4",
            "error_message": None,
        }

    async def test_empty_jobs_returns_true(self, tmp_path: Path) -> None:
        """Empty jobs list means all done — returns True."""
        self._write_jobs_json(tmp_path, [])
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True
        # No poll_job calls
        assert adapter.call_log == []

    async def test_all_terminal_no_poll(self, tmp_path: Path) -> None:
        """All jobs in terminal states — returns True without polling."""
        self._write_jobs_json(tmp_path, [self._completed_job()])
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True

    async def test_poll_updates_status(self, tmp_path: Path) -> None:
        """Generating job polled -> status updated to completed, file rewritten."""
        self._write_jobs_json(tmp_path, [self._generating_job()])
        adapter = SequenceTrackingAdapter()
        # Pre-populate submitted_jobs so poll_job can find the job
        adapter.submitted_jobs.append(
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test prompt",
                status=Veo3JobStatus.GENERATING,
            )
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True
        # File rewritten with updated status
        jobs = self._read_jobs(tmp_path)
        assert jobs[0]["status"] == "completed"
        assert jobs[0]["video_path"] == "veo3/broll.mp4"

    async def test_poll_exception_marks_poll_failed(self, tmp_path: Path) -> None:
        """When poll_job raises, the job is marked as FAILED with error_message='poll_failed'."""
        self._write_jobs_json(tmp_path, [self._generating_job()])
        adapter = SequenceTrackingAdapter()
        # Don't pre-populate — poll_job will raise for unknown key
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True
        jobs = self._read_jobs(tmp_path)
        assert jobs[0]["status"] == "failed"
        assert jobs[0]["error_message"] == "poll_failed"

    async def test_no_change_skips_write(self, tmp_path: Path) -> None:
        """If poll returns same status, jobs.json is not rewritten (mtime unchanged)."""
        self._write_jobs_json(tmp_path, [self._generating_job()])
        jobs_path = tmp_path / "veo3" / "jobs.json"
        original_content = jobs_path.read_text()

        # Mock poll_job to return same GENERATING status (no change)
        mock_adapter = AsyncMock()
        mock_adapter.poll_job = AsyncMock(
            return_value=Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test prompt",
                status=Veo3JobStatus.GENERATING,
            )
        )
        orch = Veo3Orchestrator(video_gen=mock_adapter, clip_count=3, timeout_s=300)

        result = await orch.poll_jobs(tmp_path)

        assert result is False
        # File content unchanged (no rewrite)
        assert jobs_path.read_text() == original_content

    async def test_multiple_jobs_independent_tracking(self, tmp_path: Path) -> None:
        """Multiple jobs: one succeeds, one fails poll — both tracked independently."""
        self._write_jobs_json(
            tmp_path,
            [
                self._generating_job(variant="intro", key="run1_intro"),
                self._generating_job(variant="broll", key="run1_broll"),
            ],
        )
        adapter = SequenceTrackingAdapter()
        # Only intro is known — broll poll will raise
        adapter.submitted_jobs.append(
            Veo3Job(
                idempotent_key="run1_intro",
                variant="intro",
                prompt="Test prompt",
                status=Veo3JobStatus.GENERATING,
            )
        )
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True
        jobs = self._read_jobs(tmp_path)
        statuses = {j["variant"]: j["status"] for j in jobs}
        assert statuses["intro"] == "completed"
        assert statuses["broll"] == "failed"

    async def test_missing_jobs_file_returns_true(self, tmp_path: Path) -> None:
        """Missing jobs.json -> empty list -> returns True."""
        (tmp_path / "veo3").mkdir()
        adapter = SequenceTrackingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=3, timeout_s=300)  # type: ignore[arg-type]

        result = await orch.poll_jobs(tmp_path)

        assert result is True
