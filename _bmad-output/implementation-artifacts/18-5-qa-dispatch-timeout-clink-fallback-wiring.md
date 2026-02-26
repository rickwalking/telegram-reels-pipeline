# Story 18-5: QA Dispatch Timeout & Clink Fallback Wiring

## Status: review

## Description
Wire the `dispatch_timeout_seconds` parameter in `bootstrap.py` to match the formula already used in `run_cli.py`, and add comprehensive unit tests for the clink QA dispatch fallback behaviour.

## Tasks
- [x] Task 1: Wire `dispatch_timeout_seconds` in `bootstrap.py`
  - Added `dispatch_timeout_seconds=max(300.0, settings.agent_timeout_seconds / 2)` to `CliBackend` constructor in `create_orchestrator()`
- [x] Task 2: Add unit tests for clink fallback
  - Created `tests/unit/infrastructure/test_clink_fallback.py` with 4 tests:
    - `test_clink_valid_json_returns_without_sonnet_fallback`
    - `test_clink_non_json_falls_back_to_sonnet`
    - `test_clink_exception_falls_back_to_sonnet`
    - `test_both_clink_and_sonnet_fail_raises`
- [x] Task 3: Test QA prompt size limits — SKIPPED
  - `_MAX_INLINE_BYTES` exists in `reflection_loop.py` (not in dispatch logic). Already tested in `tests/unit/application/test_reflection_loop.py::TestBuildArtifactSection`.
- [x] Task 4: Integration test for timeout propagation
  - Created `tests/unit/app/test_bootstrap_timeout.py` with parametrized tests verifying the formula across multiple agent_timeout values
- [x] Task 5: Run full test suite + linting + mypy
  - All 1348 tests pass, ruff clean, mypy clean, 92% coverage

## Dev Agent Record
- **Commit**: `fix: wire QA dispatch timeout in bootstrap and add clink fallback tests`
- **Files changed**:
  - `telegram-reels-pipeline/src/pipeline/app/bootstrap.py` (1 line added)
  - `telegram-reels-pipeline/tests/unit/infrastructure/test_clink_fallback.py` (new, 78 lines)
  - `telegram-reels-pipeline/tests/unit/app/test_bootstrap_timeout.py` (new, 53 lines)
- **Test results**: 1348 passed, 4 warnings, 92% coverage
- **Linting**: ruff clean, mypy clean
