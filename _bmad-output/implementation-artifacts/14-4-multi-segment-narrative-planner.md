# Story 14-4: Multi-Segment Narrative Planner

## Context

Building on story 14-3 (--target-duration flag), this story implements the actual narrative planning logic that the FFmpeg engineer and assembly stages use to produce a longer, coherent short from multiple transcript moments.

## Acceptance Criteria

1. **FFmpeg engineer** handles multi-moment encoding:
   - Receives `moments[]` from moment-selection.json
   - Encodes each moment as a separate segment group
   - Applies per-moment face detection and crop positioning (faces may differ between moments)
   - Generates encoding-plan with segments ordered by narrative role, not chronological order

2. **Assembly stage** handles narrative ordering:
   - Concatenates segments in narrative order (intro → buildup → core → reaction → conclusion)
   - Applies xfade transitions between narrative sections (longer dissolve between non-contiguous moments)
   - Different xfade effects for narrative boundaries vs. style transitions:
     - Style transition (solo → duo): slideright/slideleft (0.5s)
     - Narrative section boundary: dissolve (1.0s)

3. **Encoding plan schema** extended:
   - Each command gains `narrative_role` field
   - `style_transitions[]` distinguishes `style_change` from `narrative_boundary`

4. **Assembly report** includes narrative structure summary:
   - Which moments were used, in what order
   - Total screen time per narrative role

5. **Tests**: Unit tests for multi-moment assembly ordering, transition type selection

## Technical Notes

- Non-contiguous moments may have different speaker positions — each needs independent face detection
- The layout detective already extracts frames at arbitrary timestamps, so this is supported
- Longer shorts (>120s) benefit most from narrative structure; shorter ones can use a single moment
- The content creator agent prompt must emphasize narrative arc when target_duration > 90s
