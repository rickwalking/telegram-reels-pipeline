# Story 16-2: CLI --moments Flag & Auto-Trigger

## Context

Epic 14 Story 14-3 added the `--target-duration` CLI flag to `run_cli.py`, passing `target_duration_seconds` through to the workspace context. But multi-moment selection is never activated — the transcript agent always selects a single moment regardless of duration.

This story adds a `--moments N` flag for explicit control and auto-trigger logic: when `--target-duration > 120` and `--moments` is not set, the pipeline automatically activates multi-moment mode with a computed moment count. CLAUDE.md is updated to document the new flag.

## Story

As a pipeline user,
I want a `--moments N` CLI flag that explicitly requests multi-moment selection, and automatic multi-moment activation when `--target-duration > 120`,
so that I can control narrative complexity directly or let the pipeline decide based on duration.

## Acceptance Criteria

1. Given `scripts/run_cli.py`, when `--moments N` is added, then it accepts an integer 1-5 (default: None/auto)
   - `--moments 1` forces single-moment mode even for long durations
   - `--moments 3` requests exactly 3 narrative moments
   - Values outside 1-5 produce an argparse error

2. Given `--target-duration 180` without `--moments`, when the orchestrator evaluates, then `moments_requested` is auto-computed:
   - `target_duration <= 120`: moments = 1 (single-moment, current behavior)
   - `120 < target_duration <= 180`: moments = 2-3
   - `180 < target_duration <= 300`: moments = 3-5
   - Formula: `min(5, max(2, round(target_duration / 60)))`

3. Given `--moments 3 --target-duration 90`, when the orchestrator evaluates, then explicit `--moments` overrides the auto-trigger (user gets 3 moments even for a 90s target)

4. Given the workspace context, when `moments_requested` is set, then it is passed to the transcript agent alongside `target_duration_seconds`

5. Given `--moments 1`, when the pipeline runs, then it behaves identically to the current single-moment pipeline (backwards compatible)

6. Given CLAUDE.md, when the new flag is documented, then the CLI usage section includes `--moments N` with examples

## Tasks

- [ ] Task 1: Add `--moments` argparse argument to `scripts/run_cli.py`
- [ ] Task 2: Implement auto-trigger logic in orchestrator — compute `moments_requested` from `target_duration_seconds`
- [ ] Task 3: Pass `moments_requested` through workspace context to downstream agents
- [ ] Task 4: Update CLAUDE.md CLI usage section with `--moments` flag and examples
- [ ] Task 5: Unit tests for auto-trigger formula edge cases (boundary values 120, 121, 180, 300)
- [ ] Task 6: Unit tests for explicit override (--moments with --target-duration)

## Files Affected

| File | Change | Type |
|------|--------|------|
| `scripts/run_cli.py` | Add `--moments` argument, auto-trigger logic | CLI |
| `src/pipeline/application/orchestrator.py` | Compute `moments_requested`, pass to workspace context | Application |
| `CLAUDE.md` | Add `--moments` flag to CLI usage section | Documentation |
| `tests/unit/application/test_moments_auto_trigger.py` | New file — auto-trigger formula + override tests | Tests |

## Technical Notes

- The auto-trigger formula `min(5, max(2, round(target_duration / 60)))` was chosen for simplicity: 120s→2, 180s→3, 240s→4, 300s→5
- `--moments 1` is the escape hatch — forces single-moment even when duration would auto-trigger multi-moment
- The workspace context already carries `target_duration_seconds` from Story 14-3; adding `moments_requested` follows the same pattern
- No changes to domain layer — this is purely CLI + application orchestration

## Definition of Done

- `--moments N` flag working in CLI with validation (1-5)
- Auto-trigger activates for `--target-duration > 120` when `--moments` is not set
- Explicit `--moments` overrides auto-trigger
- CLAUDE.md updated with new flag documentation
- All tests pass, linters clean, mypy clean
