# Story 19-3: B-Roll Fade Transitions

## Context

The assembly stage already inserts Veo3 B-roll clips as documentary cutaway overlays. However the fade duration is hardcoded at 0.5s in `_assemble_with_cutaways()` and `_build_cutaway_filter()`, and short clips may get unreasonably long fades relative to their duration. This story adds configurable `fade_duration` with short-clip clamping (40% of clip duration max) so that B-roll overlays always look polished regardless of clip length.

## Story

As a pipeline user,
I want B-roll overlay fades to be configurable and clamped for short clips,
so that B-roll cutaways look polished at any duration without hard cuts.

## Acceptance Criteria

1. Given a B-roll clip, when overlaid, then it fades in (alpha) and fades out (alpha) using `format=yuva420p`
2. Given a standard clip (>= 2.5s), when overlaid with default fade_duration=0.5, then fade_in=0.5s and fade_out starts at duration-0.5s
3. Given a short clip (e.g. 0.8s), when overlaid, then effective fade is clamped to min(fade_duration, duration*0.4) = 0.32s
4. Given a custom fade_duration=0.3, when passed to assemble_with_broll, then it propagates to the filter graph
5. Given the filter chain order, when built, then format comes before fades, and fades come before overlay

## Tasks

- [x] Task 1: Add fade_duration parameter and short-clip clamping to `_build_cutaway_filter()` and `_assemble_with_cutaways()`
- [x] Task 2: Wire fade_duration from `assemble_with_broll()` through to `_assemble_with_cutaways()`
- [x] Task 3: Write unit tests in `tests/unit/infrastructure/test_broll_fade.py`
- [x] Task 4: Run full test suite + linting + mypy — all green

## Dev Agent Record

### Status: review

### Decisions

- Used `round(..., 4)` on computed fade values to avoid floating-point formatting artifacts (e.g. `0.32000000000000006`)
- Applied the same short-clip clamping to both `_build_cutaway_filter()` (static helper) and `_assemble_with_cutaways()` (runtime pipeline method) for consistency
- 12 new tests covering: yuva420p format, fade in/out values for standard and short clips, custom fade_duration propagation, filter chain ordering, and multiple B-roll clips

### Test Results

- 1349 tests passing
- ruff: all checks passed
- mypy: no issues found (63 source files)
- black: files formatted

### Files Changed

- `src/pipeline/infrastructure/adapters/reel_assembler.py` — configurable fade_duration with short-clip clamping
- `tests/unit/infrastructure/test_broll_fade.py` — 12 new tests (new file)
