# Story 14-3: Extended Narrative CLI Flag (--target-duration)

## Context

Currently the pipeline selects a single continuous transcript block (60-90s). Users want longer shorts that follow a narrative arc — introduction, buildup, payoff — potentially spanning multiple discontinuous sections of the source video.

A `--target-duration` flag lets the user request a longer output (e.g., 120s, 180s), and the AI agents expand the moment selection accordingly while preserving narrative structure.

## Acceptance Criteria

1. **CLI flag**: `--target-duration N` (seconds) added to `run_cli.py`
   - Default: 90 (current behavior)
   - Max: 300 (5 minutes)
   - Passed through to workspace context as `target_duration_seconds`

2. **Router stage**: Passes `target_duration_seconds` to downstream agents

3. **Transcript stage (moment selection)**: When target_duration > 90s:
   - Selects a **primary moment** (the core insight/hook)
   - Selects **supporting moments** (buildup, context, reaction) from surrounding transcript
   - Returns an ordered list of moments with narrative roles: `intro`, `buildup`, `core`, `reaction`, `conclusion`
   - Each moment has `start_seconds`, `end_seconds`, `role`, `transcript_excerpt`

4. **Content stage**: Builds a narrative plan that maps moments to the arc:
   - intro (10-15s): establishes context
   - buildup (15-30s): builds tension / sets up the core insight
   - core (30-60s): the main hook / payoff
   - reaction/conclusion (10-20s): aftermath, callback, or summary

5. **moment-selection.json** schema extended with `moments[]` array alongside existing `start_seconds`/`end_seconds` for backwards compatibility

6. **Tests**: Unit tests for duration parsing, moment ordering, narrative role assignment

## Technical Notes

- This is a prompt engineering change for stages 2-4 (transcript, content) + schema change
- The FFmpeg engineer already handles multiple segments — it just needs the moment list
- Moments can be non-contiguous (different parts of the video), creating natural transitions
- The existing xfade system handles transitions between segments
