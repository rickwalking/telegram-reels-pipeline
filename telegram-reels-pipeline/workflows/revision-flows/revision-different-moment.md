# Revision Flow: Different Moment

> **NOTE**: This is a documentation/specification file. RevisionHandler has `_REVISION_STAGES` hardcoded — it never reads this file at runtime.

## Trigger

`RevisionType.DIFFERENT_MOMENT`

User phrases: "pick a different part", "different", "another moment", "not this section", "try again"

## Stages to Re-Execute

Per `_REVISION_STAGES` in `revision_handler.py`:

1. **TRANSCRIPT** — re-analyze transcript, exclude previously selected moment
2. **CONTENT** — generate new content package for the new moment
3. **LAYOUT_DETECTIVE** — classify frames for the new moment's time range
4. **FFMPEG_ENGINEER** — encode the new moment with appropriate crop
5. **ASSEMBLY** — assemble the new segments
6. **DELIVERY** — deliver the entirely new video and content

## Handler Behavior

`_different_moment()` in RevisionHandler:
- Creates `workspace/assets/revision-hint.json` with `type="different_moment"`, `user_message`, and optional `timestamp_hint`
- The Transcript stage reads this hint and excludes the previously selected time range
- Re-executes from TRANSCRIPT stage through all downstream stages

## Context Passed to Stages

- `excluded_moments`: Array of previously selected timestamp ranges to avoid
- `user_preference`: Any additional context from the user about what they want
- `revision_hint`: JSON file with type and timestamp hint for the Transcript agent

## Incremental Re-Delivery

- **Re-deliver**: Everything — new video, new content package (descriptions, hashtags, music)
- **Preserve from original**: Research output (metadata, transcript) — doesn't need re-downloading

## Constraints

- The new moment must not overlap with the previously selected moment
- If user provided a timestamp hint, prioritize moments near that timestamp
- All downstream stages run fresh — no artifacts preserved from the original selection
- New moment must still meet all quality criteria (duration, boundaries, topic match)
