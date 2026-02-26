# Story 18-4: Await Gate Auto-Retry & Failure Classification

## Status: review

## Description
Add failure classification to the Veo3 await gate so only transient/retriable errors
trigger auto-retry, and integrate EventBus for observability on retry events.

## Tasks
- [x] Task 1: Add `_RETRIABLE_ERRORS` frozenset and `_all_failures_retriable()` helper
- [x] Task 2: Update auto-retry logic with retriability guard and differential logging
- [x] Task 3: Add `event_bus` parameter and emit `veo3.gate.retried` event
- [x] Task 4: Unit tests (22 tests covering classification, retry, guard, EventBus)
- [x] Task 5: Full test suite + linting + mypy pass

## Dev Agent Record

### Files Changed
- `src/pipeline/application/veo3_await_gate.py` — added `_RETRIABLE_ERRORS`, `_all_failures_retriable()`, `_retry_fired` guard, `event_bus` parameter, EventBus publish on retry
- `src/pipeline/application/pipeline_runner.py` — pass `event_bus=self._event_bus` to `run_veo3_await_gate()`
- `tests/unit/application/test_veo3_await_gate_retry.py` — new, 22 tests

### Test Results
- 1359 tests passed, 0 failed
- Coverage: 91.55%
- ruff: All checks passed
- mypy: Success, no issues found in 63 source files
- black: Changed files pass (pre-existing formatting issues in unrelated files)

### Design Decisions
- `_RETRIABLE_ERRORS = frozenset({"submit_failed", "rate_limited", "poll_failed"})` — matches error codes set by the orchestrator's `_submit_all()` and `poll_jobs()` methods
- `INVALID_ARGUMENT` substring check catches Gemini API validation errors regardless of the base error code
- `_retry_fired` boolean guard prevents double-retry within a single gate invocation
- `event_bus` typed as `EventBus | None` under `TYPE_CHECKING` guard to avoid import cycles
- EventBus uses `publish()` (async) matching the existing pattern throughout the codebase
