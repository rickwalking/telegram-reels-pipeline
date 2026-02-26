# Story 18-5: QA Dispatch Timeout & Clink Fallback Wiring

## Context

The QA dispatch timeout and clink/Gemini fallback are already implemented in `claude_cli_backend.py` but lack proper wiring through `bootstrap.py` and sufficient test coverage. During the first production run, QA kept failing with 500 errors from Sonnet and 429s from Gemini. The `dispatch_timeout_seconds` parameter exists on `CliBackend` but `bootstrap.py` (line 79-83) doesn't pass it — it uses the default (300s). Additionally, the clink fallback logic and QA prompt size limits need test coverage.

## Story

As a pipeline developer,
I want QA dispatch timeouts properly wired through bootstrap, and the clink/Gemini fallback to have test coverage,
so that QA evaluation doesn't timeout and token costs are optimized with verifiable fallback behavior.

## Acceptance Criteria

1. Given `bootstrap.py`, when constructing `CliBackend`, then `dispatch_timeout_seconds` is passed as `max(300.0, settings.agent_timeout_seconds / 2)`

2. Given `run_cli.py`, when it wires `CliBackend`, then its timeout wiring is consistent with the bootstrap path

3. Given clink fallback, when Gemini via clink returns no JSON `{` in response, then it falls back to Claude Sonnet — verified by test

4. Given clink fallback, when Gemini via clink raises an exception, then it falls back to Claude Sonnet — verified by test

5. Given QA prompt size, when artifacts exceed `_MAX_INLINE_BYTES=15000`, then `face-position-map.json` and `speaker-timeline.json` are sent as summary-only — verified by test

6. Given the full fallback chain, when tested end-to-end, then: clink success → uses result; clink failure → Sonnet result; both fail → `AgentExecutionError`

## Tasks

- [ ] Task 1: Wire `dispatch_timeout_seconds` in `bootstrap.py` CliBackend construction
  - [ ] Subtask 1a: Add `dispatch_timeout_seconds=max(300.0, settings.agent_timeout_seconds / 2)` to CliBackend constructor call
  - [ ] Subtask 1b: Verify `run_cli.py` uses consistent timeout wiring
- [ ] Task 2: Add unit tests for clink fallback logic in `claude_cli_backend.py`
  - [ ] Subtask 2a: Test clink success returns Gemini response
  - [ ] Subtask 2b: Test clink returns non-JSON → falls back to Sonnet
  - [ ] Subtask 2c: Test clink raises exception → falls back to Sonnet
  - [ ] Subtask 2d: Test both clink and Sonnet fail → raises `AgentExecutionError`
- [ ] Task 3: Add unit tests for QA prompt size limits
  - [ ] Subtask 3a: Test `_MAX_INLINE_BYTES` threshold triggers summary mode
  - [ ] Subtask 3b: Test `face-position-map.json` and `speaker-timeline.json` are summarized
- [ ] Task 4: Add integration test for timeout propagation through bootstrap
- [ ] Task 5: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** App (`bootstrap.py`) and Infrastructure (`claude_cli_backend.py`)
- **No behavior changes:** This story adds wiring and test coverage for existing functionality
- **Timeout formula:** `max(300.0, agent_timeout / 2)` ensures dispatch never exceeds half the agent timeout, with 300s floor

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/app/bootstrap.py` | 79-83 | `CliBackend` construction — missing `dispatch_timeout_seconds` |
| `src/pipeline/infrastructure/adapters/claude_cli_backend.py` | 39-52 | `CliBackend.__init__()` — accepts `dispatch_timeout_seconds` |
| `src/pipeline/infrastructure/adapters/claude_cli_backend.py` | 129-153 | `dispatch()` — clink first, Sonnet fallback |
| `src/pipeline/infrastructure/adapters/claude_cli_backend.py` | 167-174 | `_dispatch_via_clink()` — Gemini routing |
| `src/pipeline/infrastructure/adapters/claude_cli_backend.py` | 226-252 | `_build_clink_dispatch()` — Haiku proxy prompt |
| `src/pipeline/app/settings.py` | 32-37 | `qa_via_clink` setting |
| `src/pipeline/app/settings.py` | 55-59 | Veo3 settings (timeout reference) |

### Coding Patterns

- Test doubles should mock subprocess calls (not real CLI invocations)
- Use `unittest.mock.AsyncMock` for async method mocking
- Bootstrap tests should verify constructor args without running the full pipeline

## Definition of Done

- `dispatch_timeout_seconds` wired in `bootstrap.py`
- Clink fallback logic has full test coverage (success, JSON failure, exception)
- QA prompt size limits tested
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
