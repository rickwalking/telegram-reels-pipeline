# Story 18-4: Await Gate Auto-Retry & Failure Classification

## Context

The await gate (`veo3_await_gate.py`) already has a basic `_all_jobs_failed()` check (line 86-93) that triggers auto-retry when all jobs have `failed` status. However, it doesn't distinguish between transient failures (retriable) and permanent failures (not retriable). Story 18-3 introduced error classification in the orchestrator (`rate_limited` vs `invalid_argument`), and Story 18-2 added `download_failed` as a failure mode. The await gate needs to honor these classifications.

Additionally, the gate lacks EventBus integration — the Codex review identified that `veo3.gate.retried` events should be emitted for observability.

**Current auto-retry logic (line 55-60):**
```python
if _all_jobs_failed(jobs_path):
    logger.warning("All Veo3 jobs failed — triggering auto-retry")
    await orchestrator.start_generation(workspace, run_id)
```

This blindly retries all failures. It should only retry when failures are transient (`submit_failed`, `rate_limited`), not when they're permanent (`download_failed`, `generation_failed`, `invalid_argument`).

## Story

As a pipeline developer,
I want the await gate to distinguish transient from permanent failures and only auto-retry transient ones,
so that a bad prompt or safety violation doesn't trigger pointless re-submission.

## Acceptance Criteria

1. Given all jobs with `submit_failed` or `rate_limited` status, when the gate checks, then auto-retry is triggered

2. Given any job with `download_failed`, `generation_failed`, or `invalid_argument` error, when the gate checks, then that job is considered permanently failed — NOT retriable

3. Given a mix of retriable and permanent failures, when the gate checks, then auto-retry fires only if ALL failures are retriable

4. Given auto-retry, when it fires, then it fires at most once per await gate invocation (single-retry guard)

5. Given a successful retry, when jobs complete, then polling continues normally until completion or timeout

6. Given a failed retry, when re-submission also fails, then the gate proceeds without B-roll (emergency fallback)

7. Given the await gate, when auto-retry fires, then an EventBus event `veo3.gate.retried` is emitted

8. Given the await gate constructor, when instantiated, then it accepts an optional `EventBus` parameter

## Tasks

- [ ] Task 1: Add failure classification to await gate
  - [ ] Subtask 1a: Define `_RETRIABLE_ERRORS = frozenset({"submit_failed", "rate_limited"})` as module constant
  - [ ] Subtask 1b: Define `_PERMANENT_ERRORS = frozenset({"download_failed", "generation_failed"})` — any error_message containing "INVALID_ARGUMENT" is also permanent
  - [ ] Subtask 1c: Create `_all_failures_retriable(jobs_path: Path) -> bool` helper — returns True only if every failed job has a retriable error_message
- [ ] Task 2: Update auto-retry logic
  - [ ] Subtask 2a: Replace `_all_jobs_failed()` condition with `_all_jobs_failed() and _all_failures_retriable()`
  - [ ] Subtask 2b: Add `_retry_fired: bool` guard variable to `run_veo3_await_gate()` — set True after first retry
  - [ ] Subtask 2c: Check guard before retrying: `if not _retry_fired and _all_failures_retriable(...)`
- [ ] Task 3: Add EventBus integration
  - [ ] Subtask 3a: Add `event_bus` parameter to `run_veo3_await_gate()` signature (optional, default `None`)
  - [ ] Subtask 3b: When auto-retry fires, emit `PipelineEvent(event_name="veo3.gate.retried", ...)`
  - [ ] Subtask 3c: Import `PipelineEvent` from domain models and `EventBus` from domain
- [ ] Task 4: Unit tests
  - [ ] Subtask 4a: Test retriable failures trigger retry (`submit_failed`, `rate_limited`)
  - [ ] Subtask 4b: Test permanent failures do NOT trigger retry (`download_failed`, `generation_failed`)
  - [ ] Subtask 4c: Test mixed failures do NOT trigger retry (one permanent = no retry)
  - [ ] Subtask 4d: Test single-retry guard (second failure does NOT retry again)
  - [ ] Subtask 4e: Test EventBus event emitted on retry
  - [ ] Subtask 4f: Test EventBus is None — no crash when not provided
- [ ] Task 5: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Application (`veo3_await_gate.py`)
- **EventBus pattern:** `EventBus` is defined in `domain/` and used via the Observer pattern. Import it with TYPE_CHECKING guard
- **Backward compatibility:** `event_bus` parameter defaults to `None` — existing callers don't need to change

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/application/veo3_await_gate.py` | 21-83 | `run_veo3_await_gate()` — main function to modify |
| `src/pipeline/application/veo3_await_gate.py` | 86-93 | `_all_jobs_failed()` — existing helper |
| `src/pipeline/application/veo3_await_gate.py` | 96-112 | `_read_summary()` — reads jobs.json |
| `src/pipeline/application/veo3_await_gate.py` | 55-60 | Current auto-retry block — condition to refine |
| `src/pipeline/domain/models.py` | 381-394 | `PipelineEvent` — event to emit |
| `src/pipeline/domain/models.py` | 303-311 | `Veo3JobStatus` — status enum |
| `src/pipeline/application/veo3_orchestrator.py` | 158-164 | Error classification constants (reference) |

### Error Message Classification

| error_message | Classification | Retry? |
|--------------|----------------|--------|
| `submit_failed` | Transient (SDK not installed, network) | Yes |
| `rate_limited` | Transient (quota exhausted after 3 retries) | Yes |
| `download_failed` | Permanent (video unavailable) | No |
| `generation_failed` | Permanent (Veo3 rejected prompt) | No |
| Contains "INVALID_ARGUMENT" | Permanent (bad prompt/safety) | No |
| `poll_failed` | Transient (network during poll) | Yes |

## Definition of Done

- Failure classification distinguishes transient from permanent
- Auto-retry only fires for all-retriable failures
- Single-retry guard prevents infinite loops
- EventBus event emitted on retry (when bus provided)
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
