# Story 19-1: Two-Pass Assembly Architecture

## Context

Production debugging on 2026-02-25 revealed that the single-pass overlay approach in `reel_assembler.py` is fundamentally broken. The `_build_cutaway_filter()` method (lines 213-245) uses `overlay=enable='between(t,...)'` which fails after xfade chain because the xfade shifts the timestamp domain — the `t` variable in overlay enable expressions doesn't correspond to final timeline positions after xfade concatenation.

**Proven working approach** (verified in production with 4 B-roll overlays):
- **Pass 1:** Build base reel from segments with xfade transitions → temp file
- **Pass 2:** Overlay B-roll clips on base reel using PTS-offset technique: `setpts=PTS-STARTPTS+OFFSET/TB` + `overlay eof_action=pass`

The PTS-offset approach works because each overlay input is time-shifted to the correct position in the output timeline and `eof_action=pass` lets the base video through when the overlay ends.

**Verified FFmpeg command:**
```
[1:v]setpts=PTS-STARTPTS+0/TB[intro];
[2:v]setpts=PTS-STARTPTS+21/TB[broll];
[0:v][intro]overlay=eof_action=pass[v1];
[v1][broll]overlay=eof_action=pass[v];
-map '[v]' -map '0:a'
```

## Story

As a pipeline developer,
I want `reel_assembler.py` to use a two-pass approach for B-roll overlay assembly,
so that documentary cutaways appear at full opacity at correct timeline positions.

## Acceptance Criteria

1. Given `assemble_with_broll()`, when called with segments and B-roll placements, then it executes two distinct FFmpeg passes

2. Given Pass 1, when building the base reel, then it delegates to existing `assemble()` method with xfade transitions → writes to temp file

3. Given Pass 2, when overlaying B-roll, then each clip gets `setpts=PTS-STARTPTS+{insertion_point}/TB` to position it at the correct timeline offset

4. Given the overlay chain, when constructed, then it uses `[0:v][clip]overlay=eof_action=pass` chaining for multiple clips

5. Given audio, when assembling, then only base reel audio is used (`-map '[v]' -map '0:a'`) — B-roll clips contribute video only

6. Given a successful Pass 2, when complete, then the temp file from Pass 1 is cleaned up

7. Given a Pass 2 failure, when FFmpeg errors, then the method falls back to the base reel (Pass 1 output) as the final result

8. Given no valid B-roll placements, when `assemble_with_broll()` is called, then it delegates directly to `assemble()` (no Pass 2)

9. Given the broken `_build_cutaway_filter()` and `_assemble_with_cutaways()`, when this story is complete, then they are removed

10. Given B-roll overlays in the final reel, when verified, then clips appear at full opacity (not semi-transparent) at correct timeline positions

## Tasks

- [ ] Task 1: Create `_overlay_broll()` method in `ReelAssembler`
  - [ ] Subtask 1a: Accept `base_reel: Path`, `placements: list[BrollPlacement]`, `output: Path`
  - [ ] Subtask 1b: Build filter graph: per-clip `setpts=PTS-STARTPTS+{offset}/TB` + chained `overlay=eof_action=pass`
  - [ ] Subtask 1c: Map audio from base reel only: `-map '[v]' -map '0:a'`
  - [ ] Subtask 1d: Use `libx264 -crf 23 -preset medium -pix_fmt yuv420p` + `aac -b:a 128k` + `movflags +faststart`
  - [ ] Subtask 1e: Return output path on success
- [ ] Task 2: Refactor `assemble_with_broll()` to two-pass architecture
  - [ ] Subtask 2a: Pass 1 — call `self.assemble()` with segments + transitions → temp file
  - [ ] Subtask 2b: Pass 2 — call `self._overlay_broll()` with base reel + placements → output
  - [ ] Subtask 2c: Clean up temp file on success
  - [ ] Subtask 2d: Fall back to base reel on Pass 2 failure (log warning, rename temp → output)
- [ ] Task 3: Remove broken `_build_cutaway_filter()` (lines 213-245) and `_assemble_with_cutaways()` (lines 283-384)
- [ ] Task 4: Update `assemble_with_broll()` — skip Pass 2 if no valid placements
- [ ] Task 5: Integration tests
  - [ ] Subtask 5a: Test two-pass produces output with correct duration
  - [ ] Subtask 5b: Test B-roll appears at correct timeline position (frame extraction + pixel check)
  - [ ] Subtask 5c: Test fallback to base reel on Pass 2 failure
  - [ ] Subtask 5d: Test no-placement path delegates to `assemble()`
  - [ ] Subtask 5e: Test temp file cleanup after success
- [ ] Task 6: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Infrastructure adapter (`reel_assembler.py`)
- **Two-pass rationale:** xfade chain shifts timestamp domain, making `overlay enable='between(t,...)'` unreliable. Two separate FFmpeg invocations isolate concerns: Pass 1 handles segment concatenation, Pass 2 handles overlay positioning in a clean timeline.
- **PTS-offset technique:** `setpts=PTS-STARTPTS+OFFSET/TB` resets the clip's PTS to 0 then adds the desired timeline offset. Combined with `overlay eof_action=pass`, the base video shows through when the clip ends.

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 247-281 | `assemble_with_broll()` — entry point to refactor |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 283-384 | `_assemble_with_cutaways()` — broken single-pass, DELETE |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 213-245 | `_build_cutaway_filter()` — broken overlay builder, DELETE |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 102-136 | `assemble()` — existing base reel assembly (reuse for Pass 1) |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 168-211 | `_assemble_xfade()` — xfade filter builder (called by `assemble()`) |
| `src/pipeline/domain/models.py` | 579-600 | `BrollPlacement` — input dataclass with `insertion_point_s`, `duration_s` |

### FFmpeg Filter Graph Template (Pass 2)

```
# For N B-roll clips:
[1:v]setpts=PTS-STARTPTS+{offset_1}/TB[clip1];
[2:v]setpts=PTS-STARTPTS+{offset_2}/TB[clip2];
...
[0:v][clip1]overlay=eof_action=pass[v1];
[v1][clip2]overlay=eof_action=pass[v2];
...
# Final output: [vN]
# Audio: -map '[vN]' -map '0:a'
```

### Coding Patterns

- Async methods wrapping subprocess calls via `asyncio.create_subprocess_exec`
- Temp files in same directory as output (same filesystem for atomic rename)
- Log at `INFO` for pass completion, `WARNING` for fallback

## Definition of Done

- `assemble_with_broll()` uses two-pass approach
- `_overlay_broll()` places clips at correct timeline positions with full opacity
- Broken `_build_cutaway_filter()` and `_assemble_with_cutaways()` removed
- Fallback to base reel on Pass 2 failure
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
