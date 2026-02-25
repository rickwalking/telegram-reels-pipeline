# Story 17-6: Veo3 Clip Post-Processing & Quality Validation

## Context

Veo3-generated videos include a watermark at the bottom of each frame. The brainstorming session decided on an "always-crop" strategy — unconditional bottom strip crop on every downloaded clip, regardless of API tier. This story implements the crop + quality validation pipeline that runs BEFORE the await gate (Story 17-7) passes clips to Assembly. The await gate calls `crop_and_validate()` on each downloaded clip.

Additionally, clips must pass quality checks: correct 9:16 resolution, duration within tolerance, and no black-frame sequences (which indicate failed generation).

## Story

As a pipeline developer,
I want downloaded Veo3 clips to be automatically cropped (watermark removal) and quality-validated before the await gate passes them to Assembly,
so that only clips meeting resolution, duration, and visual quality standards enter the final reel.

## Acceptance Criteria

1. Given a downloaded Veo3 clip, when `crop_and_validate()` is called, then the bottom strip is unconditionally cropped using FFmpeg: `crop=in_w:in_h-{px}:0:0`

2. Given the crop operation, when the pixel count is determined, then it uses `VEO3_CROP_BOTTOM_PX` from settings (defined in Story 17-3, default 16)

3. Given a cropped clip, when resolution is validated, then it must match 9:16 aspect ratio (width:height ratio ≈ 0.5625)

4. Given a cropped clip, when duration is validated, then it must be within ±1s of the requested `duration_s` from the original prompt

5. Given a cropped clip, when black-frame detection runs, then clips with ≥50% consecutive black frames are flagged as failed

6. Given a clip that fails any validation check, when the result is returned, then the clip is marked as `failed` in `jobs.json` and Assembly will skip it

7. Given a clip that passes all checks, when `crop_and_validate()` returns, then it returns `True` and the cropped file replaces the original in the `veo3/` folder

8. Given the function signature, when called by the await gate, then the interface is: `crop_and_validate(clip_path: Path, expected_duration_s: int, settings: PipelineSettings) -> bool`

## Tasks

- [ ] Task 1: Create `infrastructure/adapters/veo3_postprocessor.py` with `Veo3PostProcessor` class
- [ ] Task 2: Implement FFmpeg bottom strip crop (`crop=in_w:in_h-{px}:0:0`)
- [ ] Task 3: Implement resolution validation (9:16 aspect ratio check via ffprobe)
- [ ] Task 4: Implement duration validation (±1s tolerance via ffprobe)
- [ ] Task 5: Implement black-frame detection (ffprobe or ffmpeg blackdetect filter)
- [ ] Task 6: Implement `crop_and_validate()` orchestrating crop → validate → result
- [ ] Task 7: Unit tests for crop filter construction
- [ ] Task 8: Unit tests for each validation check (pass/fail cases)
- [ ] Task 9: Integration test with a real short video clip

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/infrastructure/adapters/veo3_postprocessor.py` | New file — `Veo3PostProcessor` with crop + validation | Infrastructure adapter |
| `tests/unit/infrastructure/test_veo3_postprocessor.py` | New file — crop filter construction + validation logic tests | Tests |
| `tests/fixtures/` | Test video clips for validation testing | Test fixtures |

## Technical Notes

- FFmpeg crop filter: `ffmpeg -i input.mp4 -vf "crop=in_w:in_h-16:0:0" -c:a copy output.mp4` (crops 16px from bottom)
- The crop replaces the original file (write to tmp, validate, rename) — follows project atomic write convention
- ffprobe for metadata: `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration -of json`
- Black-frame detection: `ffmpeg -i input.mp4 -vf "blackdetect=d=0.5:pix_th=0.10" -f null -` parses stderr for black_start/black_end
- This story has NO dependency on the Gemini adapter — it operates on already-downloaded files
- The `crop_and_validate()` function is the public API that Story 17-7 (Await Gate) will call

## Definition of Done

- `Veo3PostProcessor` with crop + 3 validation checks
- `crop_and_validate()` returns bool, handles all failure modes
- Atomic file replacement after successful crop
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
