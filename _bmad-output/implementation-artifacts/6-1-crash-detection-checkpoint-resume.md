---
status: done
story: 6.1
epic: 6
title: "Crash Detection & Checkpoint Resume"
completedAt: "2026-02-11"
---

# Story 6.1: Crash Detection & Checkpoint Resume

## Implementation Notes

- `CrashRecoveryHandler` in application layer with `scan_and_recover()` method
- Uses `StateStorePort.list_incomplete_runs()` to find interrupted runs at startup
- `_build_recovery_plan()` determines resume stage from `stages_completed`
- Only counts known stage values (ignores invalid/unknown stage strings)
- `RecoveryPlan` frozen dataclass with `resume_from`, `stages_remaining`, `stages_already_done`
- Notifies user via `MessagingPort`: "Resuming your run from {stage} ({n} of {total} stages completed)"
- Notification failures are logged but never block recovery
- Wired into `main.py` startup — executes before queue polling begins
