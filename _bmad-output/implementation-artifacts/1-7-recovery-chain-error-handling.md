# Story 1.7: Recovery Chain & Error Handling

Status: done

## Story

As a developer,
I want a multi-level error recovery chain,
so that transient failures are handled automatically before escalating to the user.

## Acceptance Criteria

1. Given an agent execution fails, when the RecoveryChain processes it, then Level 1 (retry) re-executes the same agent
2. Given a retry fails, when Level 2 (fork) is attempted, then a new session is forked
3. Given a fork fails, when Level 3 (fresh) is attempted, then a completely new session executes from scratch
4. Given all recovery fails, when Level 6 (escalate) is triggered, then the user is notified via Telegram

## Tasks / Subtasks

- [x] Task 1: Implement RecoveryChain with 4 levels (AC: 1-4)
- [x] Task 2: Implement RecoveryResult and RecoveryLevel domain types
- [x] Task 3: Write comprehensive tests (11 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 258 tests passing, 96.96% coverage, all linters clean
- RecoveryChain: L1 retry → L2 fork → L3 fresh → L6 escalate
- RecoveryResult frozen dataclass, RecoveryLevel enum
- Escalation notification via optional MessagingPort (swallows notification errors)
- Fresh level strips prior_artifacts and attempt_history
- 11 new tests
- Review fix: FORK now strips attempt_history (differentiates from RETRY which passes same request)
- Review fix: added test verifying FORK strips attempt_history while keeping prior_artifacts

### File List

- src/pipeline/application/recovery_chain.py (NEW)
- tests/unit/application/test_recovery_chain.py (NEW)
