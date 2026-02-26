# Story 19-1: Two-Pass Assembly Architecture

## Context

The single-pass B-roll overlay approach (Story 17-8) builds a monolithic FFmpeg filter graph that combines base segment xfade transitions AND B-roll overlays in one command. This is fragile: xfade produces intermediate stream labels that conflict with overlay chains, causing PTS miscalculation when B-roll is inserted at specific timepoints. The two-pass approach cleanly separates concerns: Pass 1 assembles the base reel (with xfade transitions), Pass 2 overlays B-roll clips on the already-assembled base using simple PTS-offset overlay chains.

## Story

As a pipeline developer,
I want the assembly stage to use a two-pass approach for B-roll insertion (base assembly first, overlay second),
so that B-roll clips are correctly positioned using PTS offsets against a fully-assembled base reel.

## Acceptance Criteria

1. Given segments with B-roll placements, when `assemble_with_broll()` runs, then Pass 1 assembles the base reel via `assemble()` and Pass 2 overlays B-roll via `_overlay_broll()`

2. Given `_overlay_broll()`, when building the filter graph, then each clip uses `setpts=PTS-STARTPTS+{insertion_point}/TB` and chains via `overlay=eof_action=pass`

3. Given Pass 2 failure, when the overlay FFmpeg command fails, then the base reel (from Pass 1) is used as fallback output

4. Given no valid B-roll placements (all clips missing), when `assemble_with_broll()` runs, then it delegates directly to `assemble()` without Pass 2

5. Given successful Pass 2, when the overlay completes, then the temporary base reel file is deleted

6. Given the broken single-pass methods `_build_cutaway_filter()` and `_assemble_with_cutaways()`, when the refactoring is complete, then they are removed from the codebase

## Tasks

- [x] Task 1: Create `_overlay_broll()` method with PTS-offset filter graph
- [x] Task 2: Refactor `assemble_with_broll()` to two-pass (assemble -> overlay)
- [x] Task 3: Remove broken `_build_cutaway_filter()` and `_assemble_with_cutaways()` methods
- [x] Task 4: Handle no-placement edge case (delegate to `assemble()`)
- [x] Task 5: Write unit tests for two-pass assembly flow
- [x] Task 6: Run full test suite, linting, mypy — all green

## Dev Agent Record

- **Status**: done
- **Tests**: 1340 passed (full suite), 14 B-roll-specific tests (all pass)
- **Linting**: ruff clean, mypy clean, black formatted
- **Changes**:
  - `src/pipeline/infrastructure/adapters/reel_assembler.py`: Added `_overlay_broll()`, refactored `assemble_with_broll()` to two-pass, removed `_build_cutaway_filter()` and `_assemble_with_cutaways()`
  - `tests/unit/infrastructure/test_reel_assembler_broll.py`: Rewrote tests for new two-pass architecture (TestOverlayBroll, TestTwoPassFlow, TestAssembleWithBroll)
