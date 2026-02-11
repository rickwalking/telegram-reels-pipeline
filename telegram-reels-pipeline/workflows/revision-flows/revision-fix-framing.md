# Revision Flow: Fix Framing

> **NOTE**: This is a documentation/specification file. RevisionHandler has `_REVISION_STAGES` hardcoded — it never reads this file at runtime.

## Trigger

`RevisionType.FIX_FRAMING`

User phrases: "show the other speaker", "reframe", "wrong person", "crop differently", "focus on [name]"

## Stages to Re-Execute

Per `_REVISION_STAGES` in `revision_handler.py`:

1. **FFMPEG_ENGINEER** — re-encode with updated crop region targeting the requested speaker
2. **ASSEMBLY** — re-assemble with the reframed segment
3. **DELIVERY** — re-deliver the updated video

## Handler Behavior

`_fix_framing()` in RevisionHandler:
- Reads `workspace/assets/layout-segments.json`
- Marks the target segment (by index, default 0) with `needs_reframe=True`
- Adds `user_instruction` with the user's framing preference (from `request.user_message`)
- Writes to `workspace/assets/layout-segments-revised.json` (NOT the original)
- Re-executes from FFMPEG_ENGINEER stage

## Context Passed to Stages

- `original_layout`: The previous layout analysis with crop regions
- `user_instruction`: What the user wants (e.g., "show the other speaker", "focus on the guest")
- `target_segment`: Which segment to reframe (index or timestamp)

## Incremental Re-Delivery

- **Re-deliver**: Updated video file with new framing
- **Preserve from original**: Content package (descriptions, hashtags, music) — content doesn't change for reframing

## Constraints

- New crop region must be within source video bounds
- The reframed segment must maintain 1080x1920 output dimensions
- If the requested speaker is not identifiable in the frame, fall back to center-crop
