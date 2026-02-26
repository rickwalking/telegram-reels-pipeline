# Story 18-3: Rate Limit Handling & Sequential Submission

## Context

The first production run hit `429 RESOURCE_EXHAUSTED` errors when submitting Veo3 jobs because `_submit_all()` (line 156-175) uses `asyncio.gather()` to fire all jobs simultaneously. The Veo3 API has per-minute quota limits that reject burst requests. Additionally, we discovered that `400 INVALID_ARGUMENT` errors (bad prompts, safety violations) should NOT be retried — only transient errors (429, 503) are retriable.

**Production findings:**
- 3 jobs submitted in <1s → 429 on 2nd and 3rd
- After 60s cooldown, all 3 succeeded when submitted sequentially
- `503 UNAVAILABLE` also observed intermittently (Gemini capacity)

## Story

As a pipeline developer,
I want Veo3 job submission to handle rate limits with exponential backoff and sequential submission with delays,
so that the pipeline doesn't exhaust API quota by firing all jobs simultaneously.

## Acceptance Criteria

1. Given multiple Veo3 prompts, when `_submit_all()` runs, then jobs are submitted sequentially with a 5s delay between submissions (not parallel via `asyncio.gather()`)

2. Given a `429 RESOURCE_EXHAUSTED` error, when submission fails, then exponential backoff retries starting at 30s, max 3 retries per job

3. Given a `503 UNAVAILABLE` error, when submission fails, then the same exponential backoff strategy applies (transient capacity issue)

4. Given a `400 INVALID_ARGUMENT` error, when submission fails, then the job is immediately marked as `failed` with descriptive error — no retry (permanent user/config error)

5. Given retry exhaustion after 3 attempts, when all retries fail, then the job is marked as `failed` with `error_message="rate_limited"`

6. Given per-job retry, when one job hits rate limits, then other jobs' retry counters are independent

7. Given retry attempts, when they occur, then the orchestrator logs each attempt with delay duration and attempt number

## Tasks

- [ ] Task 1: Refactor `_submit_all()` from `asyncio.gather()` to sequential loop with `asyncio.sleep(5)` between submissions
- [ ] Task 2: Add `_submit_with_retry()` method to `Veo3Orchestrator`
  - [ ] Subtask 2a: Implement exponential backoff: 30s, 60s, 120s (max 3 retries)
  - [ ] Subtask 2b: Classify errors: 429/503 → retry, 400 → fail immediately, other → fail immediately
  - [ ] Subtask 2c: Log each retry attempt: `"Veo3 submit retry {attempt}/3 for {variant}, waiting {delay}s"`
- [ ] Task 3: Update `_submit_all()` to use `_submit_with_retry()` for each prompt
- [ ] Task 4: Add `submit_failed` status handling — job with `error_message` includes failure classification
- [ ] Task 5: Unit tests with `FakeVeo3Adapter` that simulates 429 errors
  - [ ] Subtask 5a: Test sequential submission (verify 5s delays)
  - [ ] Subtask 5b: Test exponential backoff timing (30s, 60s, 120s)
  - [ ] Subtask 5c: Test 400 error fails immediately (no retry)
  - [ ] Subtask 5d: Test retry exhaustion marks job as `rate_limited`
  - [ ] Subtask 5e: Test independent per-job retry counters
- [ ] Task 6: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Application (`veo3_orchestrator.py`) — retry logic lives in the orchestrator, not the adapter
- **Error classification:** The adapter raises exceptions; the orchestrator catches and classifies them
- **Backoff constants:** Could be in `settings.py` but for now hardcode in orchestrator (YAGNI — no user-facing config needed)

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/application/veo3_orchestrator.py` | 156-175 | `_submit_all()` — currently uses `asyncio.gather()` for parallel submission |
| `src/pipeline/application/veo3_orchestrator.py` | 46-73 | `start_generation()` — calls `_submit_all()` |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 44-72 | `submit_job()` — raises on API errors |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 96-142 | `FakeVeo3Adapter` — needs `simulate_429` flag for testing |
| `src/pipeline/domain/models.py` | 303-311 | `Veo3JobStatus` — `FAILED` status used for rate-limited jobs |

### Error Classification Table

| Error Code | Error Type | Action | Retry? |
|-----------|------------|--------|--------|
| 429 | RESOURCE_EXHAUSTED | Exponential backoff | Yes (3x) |
| 503 | UNAVAILABLE | Exponential backoff | Yes (3x) |
| 400 | INVALID_ARGUMENT | Fail immediately | No |
| Other | Unknown | Fail immediately | No |

### Coding Patterns

- `asyncio.sleep()` for delays (non-blocking)
- Exception chaining: `raise Veo3GenerationError(...) from e`
- Log via `logging.getLogger(__name__)` at `WARNING` for retries, `ERROR` for failures

## Definition of Done

- `_submit_all()` is sequential with 5s delays
- Exponential backoff (30s, 60s, 120s) on 429/503
- 400 errors fail immediately (no retry)
- Per-job retry independence
- All tests pass, linters clean, mypy clean
- Min 80% coverage on changed code

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log

## Status

ready-for-dev
