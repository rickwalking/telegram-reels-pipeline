# Story 18-3: Rate Limit Handling & Sequential Submission

## Context

The Veo3 orchestrator originally fired all generation jobs in parallel via `asyncio.gather()`. This causes rate-limit errors (HTTP 429, RESOURCE_EXHAUSTED) from the Gemini API when submitting multiple clips simultaneously. This story refactors submission to be sequential with inter-submission delays and adds exponential backoff retry logic for transient API errors.

## Story

As a pipeline developer,
I want sequential Veo3 job submission with exponential backoff on rate limits,
so that the pipeline handles API rate limits gracefully without losing jobs.

## Acceptance Criteria

1. Given multiple Veo3 prompts, when `_submit_all()` runs, then jobs are submitted one at a time (not via `asyncio.gather()`)

2. Given sequential submission, when each job is submitted, then a 5-second delay is inserted between submissions (but not after the last one)

3. Given a retryable API error (429, RESOURCE_EXHAUSTED, 503, UNAVAILABLE), when submission fails, then it retries with exponential backoff (30s, 60s, 120s)

4. Given a permanent API error (400, INVALID_ARGUMENT), when submission fails, then it fails immediately without retry

5. Given 3 consecutive retryable failures, when all retries are exhausted, then the job is marked FAILED with `error_message="rate_limited"`

6. Given multiple jobs, when one job's retry fails, then other jobs' retry counters are independent and unaffected

## Tasks

- [x] Task 1: Refactor `_submit_all()` to sequential loop with `asyncio.sleep(5)` between submissions
- [x] Task 2: Add `_submit_with_retry()` method with exponential backoff (30s, 60s, 120s)
- [x] Task 3: Wire `_submit_with_retry()` into `_submit_all()` replacing direct `submit_job()` calls
- [x] Task 4: Error classification via string matching on `str(e)` for broad exception handling
- [x] Task 5: Unit tests in `tests/unit/application/test_veo3_retry.py`
- [x] Task 6: Run full test suite + linting + mypy

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/application/veo3_orchestrator.py` | Refactored `_submit_all()` from parallel to sequential; added `_submit_with_retry()`, `_is_retryable()` | Application layer |
| `tests/unit/application/test_veo3_retry.py` | New file -- 23 tests for retry logic, sequential submission, backoff | Tests |
| `tests/unit/application/test_veo3_orchestrator.py` | Updated test name from `test_parallel_submission` to `test_sequential_submission` | Tests |

## Technical Notes

- Error classification uses string matching on `str(e)` to handle diverse exception types from google-genai SDK
- Backoff delays are class constants `_BACKOFF_DELAYS = (30, 60, 120)` for easy tuning
- Inter-submission delay is `_INTER_SUBMIT_DELAY = 5` seconds
- `_is_retryable()` is a static method checking for `_RETRYABLE_PATTERNS = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")`
- The retry loop uses `for attempt in range(1, _MAX_RETRIES + 1)` with `continue` on retryable + not exhausted

## Dev Agent Record

- **Status**: review
- **Tests**: 1360 passed (full suite), 46 in retry + orchestrator files
- **Lint**: ruff clean, mypy clean, black clean on changed files
- **Coverage**: veo3_orchestrator.py at 70% (uncovered lines are poll_jobs and file I/O paths)

## Definition of Done

- Sequential submission with inter-submission delays
- Exponential backoff retry for rate-limit / server errors
- Immediate failure for client errors
- All tests pass, linters clean, mypy clean
