# Revision Flow: Extend Moment

> **NOTE**: This is a documentation/specification file. RevisionHandler has `_REVISION_STAGES` hardcoded — it never reads this file at runtime. This serves as human-readable reference for the revision system design.

## Trigger

`RevisionType.EXTEND_MOMENT`

User phrases: "make it longer", "extend", "more seconds", "too short", "include more"

## Stages to Re-Execute

Per `_REVISION_STAGES` in `revision_handler.py`:

1. **FFMPEG_ENGINEER** — re-encode with extended timestamps
2. **ASSEMBLY** — re-assemble with the extended segment
3. **DELIVERY** — re-deliver the updated video

## Handler Behavior

`_extend_moment()` in RevisionHandler:
- Reads `workspace/assets/moment-selection.json`
- Adjusts `start_seconds` by `-extra_seconds` (default 15s), clamped to >= 0
- Adjusts `end_seconds` by `+extra_seconds` (default 15s)
- Writes to `workspace/assets/moment-selection-revised.json` (NOT the original)
- Re-executes from FFMPEG_ENGINEER stage

Note: Code only clamps start to >= 0. No upper duration cap is implemented in the handler.

## Context Passed to Stages

- `original_moment`: The previous moment-selection.json (start/end timestamps)
- `user_request`: The interpreted extension request
- `adjustment`: -15s start, +15s end (total +30s extension)

## Incremental Re-Delivery

- **Re-deliver**: Updated video file, updated assembly report
- **Preserve from original**: Content package (descriptions, hashtags, music) — content doesn't change for extensions

## Constraints

- Start is clamped to >= 0 (code enforces this)
- No upper duration cap is currently implemented in the handler — MomentSelection validation (30-120s) only applies when the domain model is constructed downstream
- Quality gate re-evaluation on the new encoding
