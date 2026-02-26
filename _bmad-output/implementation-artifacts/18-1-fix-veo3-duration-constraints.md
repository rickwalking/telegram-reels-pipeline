# Story 18-1: Fix Veo3 Duration Constraints

## Context

The first production run (workspace `20260225-131343-911335`) revealed that the Veo3 API (`veo-3.1-generate-preview`) only accepts **even** duration values: 4, 6, 8. Odd values (5, 7) are rejected with `400 INVALID_ARGUMENT`. The current adapter passes `duration_seconds` as a string and the domain model validates 5-8, allowing invalid odd values through. Additionally, when `duration_s` is 0 (unset), the adapter defaults to `"6"` as a string instead of `int`.

**Root cause:** `gemini_veo3_adapter.py:58` passes `duration_seconds=str(prompt.duration_s)` — should be `int` and must clamp to even values.

## Story

As a pipeline developer,
I want the adapter to enforce Veo3 API duration constraints (even-only values: 4, 6, 8),
so that generation requests never fail with `INVALID_ARGUMENT` for out-of-bound durations.

## Acceptance Criteria

1. Given a `Veo3Prompt` with odd `duration_s` (5 or 7), when `submit_job()` is called, then the adapter clamps to the nearest valid even value (5→6, 7→8)

2. Given a `Veo3Prompt` with `duration_s` below 4, when `submit_job()` is called, then the adapter clamps to 4

3. Given a `Veo3Prompt` with `duration_s` above 8, when `submit_job()` is called, then the adapter clamps to 8

4. Given a `Veo3Prompt` with `duration_s` of 0 (unset), when `submit_job()` is called, then the adapter defaults to 6

5. Given the `duration_seconds` parameter in the API call, when constructed, then it is passed as `int` (not `str`)

6. Given the domain model `Veo3Prompt`, when validation runs, then `duration_s` accepts 0 (auto) or 4-8 inclusive (relaxed from 5-8)

7. Given the orchestrator `_convert_prompts()`, when it processes raw prompts, then it passes through raw duration values — clamping is the adapter's responsibility

## Tasks

- [ ] Task 1: Add `_clamp_duration(duration_s: int) -> int` static method to `GeminiVeo3Adapter`
  - [ ] Subtask 1a: Implement clamping logic: 0→6, <4→4, >8→8, odd→round up to next even
  - [ ] Subtask 1b: Log when clamping occurs (original vs clamped value)
- [ ] Task 2: Update `submit_job()` to use `_clamp_duration()` and pass `int` not `str`
- [ ] Task 3: Relax `Veo3Prompt.__post_init__` validation to accept `duration_s` in {0} ∪ [4,8]
- [ ] Task 4: Update `FakeVeo3Adapter.submit_job()` to match new duration handling
- [ ] Task 5: Unit tests for `_clamp_duration()` — all edge cases: 0→6, 3→4, 4→4, 5→6, 6→6, 7→8, 8→8, 9→8
- [ ] Task 6: Unit tests for relaxed `Veo3Prompt` validation (0 valid, 4 valid, 9 invalid)
- [ ] Task 7: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Infrastructure adapter (`gemini_veo3_adapter.py`) owns clamping; domain model (`models.py`) owns validation range
- **Single responsibility:** Orchestrator (`veo3_orchestrator.py:134-154`) passes through raw duration — adapter is the boundary where API constraints are enforced
- **Hexagonal rule:** Domain model validates broad correctness (0 or 4-8); adapter enforces API-specific even-only constraint

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 44-72 | `submit_job()` — line 58 passes `duration_seconds=str(prompt.duration_s)` |
| `src/pipeline/domain/models.py` | 261-288 | `Veo3Prompt` — line 280-281 validates `5 <= duration_s <= 8` |
| `src/pipeline/application/veo3_orchestrator.py` | 134-154 | `_convert_prompts()` — passes through raw duration |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 96-142 | `FakeVeo3Adapter` — test double |
| `tests/unit/domain/test_veo3_models.py` | — | Existing domain model tests |

### Coding Patterns

- Frozen dataclasses, `__post_init__` validation with `ValueError`
- Adapter methods are `async` even for pure transforms (port protocol)
- Log via `logging.getLogger(__name__)`

## Definition of Done

- `_clamp_duration()` handles all edge cases
- `submit_job()` passes `int` to API
- `Veo3Prompt` validation relaxed to 0 or 4-8
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
