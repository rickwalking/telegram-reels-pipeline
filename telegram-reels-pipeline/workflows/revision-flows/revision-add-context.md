# Revision Flow: Add Context

> **NOTE**: This is a documentation/specification file. RevisionHandler has `_REVISION_STAGES` hardcoded — it never reads this file at runtime.

## Trigger

`RevisionType.ADD_CONTEXT`

User phrases: "add more context", "context", "need the setup", "include the question", "what came before"

## Stages to Re-Execute

Per `_REVISION_STAGES` in `revision_handler.py`:

1. **FFMPEG_ENGINEER** — re-encode with widened timestamps
2. **ASSEMBLY** — re-assemble with the extended segment
3. **DELIVERY** — re-deliver the updated video

## Handler Behavior

`_add_context()` in RevisionHandler:
- Reads `workspace/assets/moment-selection.json`
- Widens `start_seconds` by `-extra_seconds` (default 30s), clamped to >= 0
- Widens `end_seconds` by `+extra_seconds` (default 30s)
- Sets `context_added=True` and `user_instruction` in the data
- Writes to `workspace/assets/moment-selection-revised.json` (NOT the original)
- Re-executes from FFMPEG_ENGINEER stage

## Context Passed to Stages

- `original_moment`: The previous moment selection with original timestamps
- `user_request`: The interpreted context request
- `adjustment`: -30s start, +30s end (total +60s context addition)
- `context_added`: True (flag to indicate this is a context-expanded version)

## Incremental Re-Delivery

- **Re-deliver**: Updated video file with more context
- **Preserve from original**: Content package (descriptions, hashtags, music) — content may still be relevant

## Constraints

- Start is clamped to >= 0 (code enforces this)
- No upper duration cap is currently implemented in the handler — MomentSelection validation (30-120s) only applies when the domain model is constructed downstream
- Adding context is more aggressive than extending (±30s vs ±15s)
- Layout analysis may need updating if new timestamps include different layouts (but per code, LAYOUT_DETECTIVE is not re-run for ADD_CONTEXT)
