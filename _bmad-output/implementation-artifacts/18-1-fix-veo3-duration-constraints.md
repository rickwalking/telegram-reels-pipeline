# Story 18-1: Fix Veo3 Duration Constraints

## Status: review

## Context

The Veo3 API only accepts even-second durations in [4, 8]. The current adapter passes the raw `duration_s` as a string, which can cause API rejections for odd values or values outside the range. The domain model validation is also too restrictive (5-8 instead of 4-8).

## Story

As a pipeline developer,
I want the Veo3 adapter to clamp durations to valid even values and pass them as integers,
so that Veo3 API calls never fail due to invalid duration parameters.

## Acceptance Criteria

1. Given `_clamp_duration(0)`, when called, then it returns 6 (default)
2. Given `_clamp_duration(n)` where n < 4, when called, then it returns 4
3. Given `_clamp_duration(n)` where n > 8, when called, then it returns 8
4. Given `_clamp_duration(n)` where n is odd and in [4,8], when called, then it rounds up to the next even value
5. Given `_clamp_duration(n)` where n is even and in [4,8], when called, then it passes through unchanged
6. Given `submit_job()`, when duration is passed, then it uses `_clamp_duration()` and passes the result as `int` (not `str`)
7. Given `Veo3Prompt(duration_s=4)`, when constructed, then it is valid (was previously rejected)
8. Given `Veo3Prompt(duration_s=0)`, when constructed, then it is valid (auto/unset)
9. Given `Veo3Prompt(duration_s=3)`, when constructed, then it raises `ValueError`

## Tasks

- [x] Task 1: Add `_clamp_duration()` static method to `GeminiVeo3Adapter`
- [x] Task 2: Update `submit_job()` to use `_clamp_duration()` and pass `int` (not `str`)
- [x] Task 3: Relax `Veo3Prompt.__post_init__` validation from `5-8` to `4-8` (allow 0 as auto)
- [x] Task 4: Update `FakeVeo3Adapter.submit_job()` to apply same clamping
- [x] Task 5: Unit tests for `_clamp_duration()` edge cases
- [x] Task 6: Update existing domain tests for relaxed 4-8 range
- [x] Task 7: Run full test suite + linting + mypy — all green

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | Add `_clamp_duration()`, update `submit_job()`, update `FakeVeo3Adapter` | Infrastructure adapter |
| `src/pipeline/domain/models.py` | Relax `Veo3Prompt` validation from 5-8 to 4-8 | Domain model |
| `tests/unit/infrastructure/test_veo3_duration_clamp.py` | New file — clamp + validation tests | Tests |
| `tests/unit/domain/test_veo3_models.py` | Update range assertions from 5-8 to 4-8 | Tests |
| `tests/unit/test_content_creator_output.py` | Update range assertions from 5-8 to 4-8 | Tests |

## Dev Agent Record

- **Agent Model**: claude-opus-4-6
- **Completion Notes**: All 7 tasks completed. Added `_clamp_duration()` as a `@staticmethod` on `GeminiVeo3Adapter` with full edge-case handling (0->6 default, <4->4, >8->8, odd->round up, even passthrough). Updated `submit_job()` to pass clamped int instead of string. Relaxed domain validation from 5-8 to 4-8 with 0 still allowed. Updated `FakeVeo3Adapter` for consistency. Created 18 new tests, updated 8 existing tests. Full suite: 1356 tests pass, ruff clean, mypy clean.
- **Change Log**:
  - `gemini_veo3_adapter.py`: Added `_clamp_duration()` staticmethod, changed `duration_seconds=str(...)` to `duration_seconds=clamped` (int), added clamping call in `FakeVeo3Adapter.submit_job()`
  - `models.py`: Changed `5 <= self.duration_s <= 8` to `4 <= self.duration_s <= 8`, updated error message
  - `test_veo3_duration_clamp.py`: New file with 18 tests covering clamp edge cases and relaxed validation
  - `test_veo3_models.py`: Updated valid range to include 4, changed rejection boundary from 4 to 3, updated error match strings
  - `test_content_creator_output.py`: Updated valid range to include 4, changed rejection boundary from 4 to 3, updated error match strings
