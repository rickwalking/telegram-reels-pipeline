# Story 19-3: B-Roll Fade Transitions

## Context

Story 19-1 implemented the two-pass B-roll overlay using `setpts=PTS-STARTPTS+OFFSET/TB` + `overlay=eof_action=pass`. The clips currently hard-cut in and out. This story adds fade-in/fade-out transitions on the alpha channel so documentary cutaways appear and disappear smoothly.

**Edge case from Codex review:** Clips shorter than 1.0s would have overlapping fades if using the default 0.5s fade duration. The formula `min(0.5, dur * 0.4)` handles this gracefully.

The fade is applied to the B-roll clip's alpha channel BEFORE the PTS shift in the filter graph. The base reel audio continues uninterrupted — fades are visual only.

## Story

As a pipeline developer,
I want B-roll clips to fade in/out smoothly at their insertion boundaries,
so that the cutaway transitions feel polished rather than jarring hard cuts.

## Acceptance Criteria

1. Given a B-roll clip, when overlaid, then it fades in over 0.5s at the start and fades out over 0.5s at the end

2. Given the fade filter, when applied, then it uses `format=yuva420p,fade=t=in:st=0:d={fade}:alpha=1,fade=t=out:st={dur-fade}:d={fade}:alpha=1` before the PTS shift

3. Given a clip shorter than 1.0s (e.g., 0.8s), when faded, then the fade duration is reduced to `min(0.5, dur * 0.4)` to avoid overlapping fades

4. Given the fade, when applied, then it affects only the video alpha channel — audio continues uninterrupted

5. Given the `_overlay_broll()` method, when constructing the filter, then fade is configurable via a `fade_duration` parameter (default 0.5)

## Tasks

- [ ] Task 1: Add fade filter to `_overlay_broll()` filter graph
  - [ ] Subtask 1a: Add `fade_duration: float = 0.5` parameter to `_overlay_broll()`
  - [ ] Subtask 1b: For each clip, compute effective fade: `eff_fade = min(fade_duration, bp.duration_s * 0.4)`
  - [ ] Subtask 1c: Prepend alpha fade filters before PTS shift: `[{i}:v]format=yuva420p,fade=t=in:st=0:d={eff_fade}:alpha=1,fade=t=out:st={dur-eff_fade}:d={eff_fade}:alpha=1,setpts=PTS-STARTPTS+{offset}/TB[clip{i}]`
- [ ] Task 2: Wire fade_duration parameter from `assemble_with_broll()` to `_overlay_broll()`
  - [ ] Subtask 2a: Add `fade_duration: float = 0.5` parameter to `assemble_with_broll()`
  - [ ] Subtask 2b: Pass through to `_overlay_broll()`
- [ ] Task 3: Unit tests
  - [ ] Subtask 3a: Test filter graph contains `format=yuva420p` and `fade=t=in` and `fade=t=out`
  - [ ] Subtask 3b: Test standard clip (6s) uses 0.5s fade
  - [ ] Subtask 3c: Test short clip (0.8s) uses reduced fade (0.32s = 0.8 * 0.4)
  - [ ] Subtask 3d: Test custom fade_duration parameter propagates
  - [ ] Subtask 3e: Test fade filter appears BEFORE setpts in the filter chain
- [ ] Task 4: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Infrastructure adapter (`reel_assembler.py`)
- **Filter chain order:** `format=yuva420p` → `fade in` → `fade out` → `setpts=PTS-STARTPTS+OFFSET/TB` — fade must be applied before PTS shift because fade timing is relative to clip start (0s)
- **Alpha channel:** `format=yuva420p` enables alpha channel, `alpha=1` in fade filter means it fades the alpha (transparency) not the pixel values

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 213-289 | `_overlay_broll()` — add fade filters here |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 236-239 | Current filter: `setpts=PTS-STARTPTS+{offset}/TB` — prepend fade before this |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 291-338 | `assemble_with_broll()` — wire fade_duration parameter |
| `src/pipeline/domain/models.py` | 579-600 | `BrollPlacement.duration_s` — used to compute effective fade |

### Filter Graph Example

Before (19-1):
```
[1:v]setpts=PTS-STARTPTS+21/TB[clip1]
```

After (19-3, standard 6s clip):
```
[1:v]format=yuva420p,fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st=5.5:d=0.5:alpha=1,setpts=PTS-STARTPTS+21/TB[clip1]
```

After (19-3, short 0.8s clip):
```
[1:v]format=yuva420p,fade=t=in:st=0:d=0.32:alpha=1,fade=t=out:st=0.48:d=0.32:alpha=1,setpts=PTS-STARTPTS+21/TB[clip1]
```

## Definition of Done

- B-roll clips fade in/out at insertion boundaries
- Short clips get proportionally reduced fade
- Alpha-only fades, audio uninterrupted
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
