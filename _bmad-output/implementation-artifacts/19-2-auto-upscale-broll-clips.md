# Story 19-2: Auto-Upscale B-Roll Clips

## Context

Story 19-1 implemented the two-pass assembly architecture where Pass 2 overlays B-roll clips on the base reel. However, Veo3 generates clips at 720x1280 while segments are 1080x1920. During the first production run, we had to manually upscale clips with `ffmpeg -vf 'scale=1080:1920:flags=lanczos'` before overlay. This step needs to be automated as a pre-processing step before Pass 2.

Story 20-1's `ExternalClipDownloader` already handles upscaling internally for external clips. This story adds the same capability to the reel assembler for Veo3 clips (and any other B-roll source), ensuring ALL clips entering Pass 2 match the target 1080x1920 resolution.

**Target resolution is hardcoded** to 1080x1920 per Gemini review — no inference from segments needed.

## Story

As a pipeline developer,
I want B-roll clips automatically upscaled to 1080x1920 before overlay,
so that resolution mismatches don't cause visual artifacts in the final reel.

## Acceptance Criteria

1. Given a B-roll clip at 720x1280, when passed to the assembler, then it is automatically upscaled to 1080x1920 before overlay

2. Given the upscaling method, when applied, then it uses `scale=1080:1920:flags=lanczos` for quality

3. Given upscaling, when it happens, then it occurs as a pre-processing step BEFORE the Pass 2 overlay filter graph — not inside it

4. Given upscaled clips, when created, then they are written to a temp directory and cleaned up after assembly

5. Given a clip already at 1080x1920, when checked, then upscaling is skipped (no-op fast path)

6. Given the target resolution, when referenced, then it is hardcoded as 1080x1920 (not derived from segments)

## Tasks

- [ ] Task 1: Add `_probe_resolution()` static method to `ReelAssembler`
  - [ ] Subtask 1a: Run `ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json`
  - [ ] Subtask 1b: Parse JSON output, return `tuple[int, int]` (width, height)
  - [ ] Subtask 1c: Return `(0, 0)` on any failure (triggers upscale as safety net)
- [ ] Task 2: Add `_upscale_clip()` static method to `ReelAssembler`
  - [ ] Subtask 2a: Run `ffmpeg -i input -vf 'scale=1080:1920:flags=lanczos' -c:a copy output`
  - [ ] Subtask 2b: Write to temp path, return path on success
  - [ ] Subtask 2c: Raise `AssemblyError` on FFmpeg failure
- [ ] Task 3: Add `_ensure_clip_resolution()` method to `ReelAssembler`
  - [ ] Subtask 3a: Probe clip resolution via `_probe_resolution()`
  - [ ] Subtask 3b: If already 1080x1920, return original path (no-op)
  - [ ] Subtask 3c: If different, upscale via `_upscale_clip()` to temp dir, return new path
  - [ ] Subtask 3d: Track temp files for cleanup
- [ ] Task 4: Wire `_ensure_clip_resolution()` into `assemble_with_broll()`
  - [ ] Subtask 4a: After validating placements, upscale each clip before Pass 2
  - [ ] Subtask 4b: Create new `BrollPlacement` instances with updated `clip_path` for upscaled clips
  - [ ] Subtask 4c: Clean up temp upscaled clips after Pass 2 completes (success or failure)
- [ ] Task 5: Add constants `_TARGET_WIDTH = 1080` and `_TARGET_HEIGHT = 1920`
- [ ] Task 6: Unit tests
  - [ ] Subtask 6a: Test `_probe_resolution()` parses ffprobe JSON correctly
  - [ ] Subtask 6b: Test `_probe_resolution()` returns (0,0) on failure
  - [ ] Subtask 6c: Test `_upscale_clip()` builds correct FFmpeg command
  - [ ] Subtask 6d: Test `_ensure_clip_resolution()` skips upscale for 1080x1920
  - [ ] Subtask 6e: Test `_ensure_clip_resolution()` upscales for 720x1280
  - [ ] Subtask 6f: Test temp file cleanup after assembly
- [ ] Task 7: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Infrastructure adapter (`reel_assembler.py`)
- **Pre-processing model:** Upscale happens BEFORE the overlay filter graph, not inside it. This keeps the filter graph simple and avoids scale filters mixed with overlay chains.
- **Temp files:** Upscaled clips written to `output.parent / "_upscaled_{stem}.mp4"`, cleaned in `finally` block
- **BrollPlacement is frozen:** Can't modify `clip_path` in-place. Create new instances with `dataclasses.replace(bp, clip_path=str(upscaled_path))`

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 291-338 | `assemble_with_broll()` — wire upscale before Pass 2 |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 213-289 | `_overlay_broll()` — Pass 2 method (receives already-upscaled clips) |
| `src/pipeline/domain/models.py` | 579-600 | `BrollPlacement` — frozen dataclass |
| `src/pipeline/infrastructure/adapters/external_clip_downloader.py` | 153-179 | `_probe_resolution()` — reference pattern to follow |
| `src/pipeline/infrastructure/adapters/external_clip_downloader.py` | 181-204 | `_upscale()` — reference pattern to follow |

### FFmpeg Commands

```bash
# Probe resolution
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of json input.mp4

# Upscale
ffmpeg -i input.mp4 -vf 'scale=1080:1920:flags=lanczos' -c:a copy output.mp4
```

## Definition of Done

- Clips auto-upscaled to 1080x1920 before overlay
- No-op fast path for correct resolution
- Temp files cleaned up
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
