# QA Gate: Assembly

## Evaluation Dimensions

### Dimension 1: Final Video Existence (weight: 25/100)
- **Pass**: Final video file exists, is non-empty, and is a valid MP4 container
- **Rework**: File exists but is suspiciously small (< 1MB for a 30+ second video)
- **Fail**: File does not exist or is corrupt (not a valid MP4)
- **Prescriptive fix template**: "Final video file not found at {path}. Check that concatenation completed successfully and output path matches assembly plan."

### Dimension 2: Dimensions Compliance (weight: 25/100)
- **Pass**: Final video is exactly 1080x1920
- **Rework**: Dimensions are close but not exact (within 4px)
- **Fail**: Dimensions are wrong (not 1080x1920)
- **Prescriptive fix template**: "Final video is {actual_w}x{actual_h} instead of 1080x1920. Check that all input segments have matching dimensions before concatenation."

### Dimension 3: Duration Accuracy (weight: 25/100)
- **Pass**: Duration is within 5% of expected (single-moment) or 15% of `target_duration_seconds` (multi-moment, from `narrative_summary`)
- **Rework**: Duration is within 5-10% (single-moment) or 15-20% (multi-moment) of expected
- **Fail**: Duration mismatch > 10% (single-moment) or > 20% (multi-moment)
- **Prescriptive fix template**: "Final duration {actual}s vs expected {expected}s (difference: {diff}%). Check concatenation order — segment {n} may be missing or duplicated."
- **Boundary trim exemption**: When `encoding-plan.json` contains segments with `boundary_validation.start_trimmed: true` or `boundary_validation.end_trimmed: true`, recalculate the expected duration by subtracting the total trimmed seconds. A 1–2s gap per camera transition is intentional and should not count as a duration mismatch.
- **Cumulative trim cap**: If total trimmed seconds across all segments exceeds 5.0s, flag as **Fail** regardless of the trim exemption. Excessive trimming indicates a systemic boundary detection problem that needs investigation.

### Dimension 4: Audio Sync (weight: 25/100)
- **Pass**: Audio is present and synchronized with video
- **Rework**: Audio present but minor desync (< 0.5s drift)
- **Fail**: No audio, or audio is severely desynced (> 1s drift)
- **Prescriptive fix template**: "Audio desync detected ({drift}s drift). Re-concatenate with matching audio parameters across all segments. Ensure all segments have same audio sample rate (44100 Hz)."

### Dimension 5: Transition Quality (weight: 0/100 when no transitions, redistributed from others)
- **Pass**: xfade transitions render smoothly, no visual glitches at transition boundaries, duration matches spec (0.5s)
- **Rework**: xfade transitions present but minor artifacts (single-frame flash, slight audio pop)
- **Fail**: xfade transitions cause video corruption or significant visual artifacts
- **Prescriptive fix template**: "xfade transition at {offset}s has visual artifacts. Fall back to hard-cut concat for this transition boundary."
- **Rework** (framing mismatch at join): For multi-segment reels, check the last frame of segment N and first frame of segment N+1. If the visual framing style changes abruptly without a transition effect (e.g., split-screen suddenly becomes solo crop with no fade), flag as rework. This catches Boundary Frame Guard gaps where trimming created a visual discontinuity.
- **Prescriptive fix template** (framing mismatch): "Join between segment {n} and {n+1} shows abrupt framing change ({style_a} → {style_b}) with no transition. Either add an xfade transition at this boundary or verify that the FFmpeg Engineer's boundary_validation correctly trimmed the camera transition frames."

**Note**: This dimension has two independent sub-checks:
- **xfade artifact checks** (Pass/Rework/Fail above): Only evaluated when xfade transitions are present. When all transitions are hard cuts and the reel is single-segment, this dimension's weight (0) is redistributed equally to dimensions 1-4 (6.25 each, totaling 25 per dimension).
- **Framing mismatch at join** (Rework above): Evaluated for ALL multi-segment reels, regardless of whether xfade is used. This catches boundary-trim gaps and hard-cut style discontinuities.
- **Multi-segment weight**: For multi-segment reels, Dimension 5 weight is **10/100** (redistributed from Dimensions 1-4, reducing each by 2.5) to account for framing mismatch checks at segment joins.

## Scoring Rubric

- 90-100: Excellent — perfect dimensions, duration matches, audio synced, valid file
- 70-89: Good — file exists, dimensions correct, minor duration or sync issues
- 50-69: Acceptable — file exists but some quality concerns
- 30-49: Poor — rework required, duration mismatch or quality issues
- 0-29: Fail — no valid output or fundamentally broken

## Multi-Moment Dimensions (when `narrative_summary` present)

When the assembly report contains a `narrative_summary` (multi-moment mode), apply standard dimensions above plus these additional checks:

### Dimension 6: Narrative Ordering (weight: 10/100, redistributed from Dim 1-4)

- **Pass**: Segments appear in correct narrative role order in the final Reel (intro → buildup → core → reaction → conclusion)
- **Rework**: Segments are in correct role order but one moment's internal segments are out of order
- **Fail**: Segments are in wrong narrative role order (e.g., conclusion before core)
- **Prescriptive fix template**: "Segments are in {actual_order} instead of narrative order. Reorder so that {expected_order} is used."

### Dimension 7: Transition Consistency (weight: 5/100, redistributed from Dim 1-4)

- **Pass**: `narrative_boundary` transitions (1.0s dissolve) are used between moments, `style_change` transitions (0.5s slide) within moments
- **Rework**: Transition types are present but durations don't match spec
- **Fail**: No transitions between moments or wrong transition types
- **Prescriptive fix template**: "Transition between moment {i} and {j} uses {actual_type} instead of narrative_boundary dissolve. Update the transition to use 1.0s dissolve between narrative moments."

### Weight Redistribution (multi-moment)

| Dimension | Single-moment | Multi-moment |
|-----------|--------------|--------------|
| Final Video Existence | 25 | 20 |
| Dimensions Compliance | 25 | 20 |
| Duration Accuracy | 25 | 20 |
| Audio Sync | 25 | 15 |
| Transition Quality | 0-10 | 10 |
| Narrative Ordering | — | 10 |
| Transition Consistency | — | 5 |

## Output Schema Requirements

Output JSON (`assembly-report.json`) must contain:
- `concatenation_order`: array of segment paths in order
- `transitions`: array of transition specs (type, at_seconds, transition_kind)
- `final_output_path`: string path to final video
- `quality_checks`: object with dimensions, duration_seconds, file_size_mb, codec, audio_codec, all_segments_valid, duration_within_tolerance
- `boundary_trims`: array (optional, present when boundary trims exist) — each entry has `segment` (int), `boundary` ("start" or "end"), `original_seconds` (float), `adjusted_seconds` (float), `trimmed_duration` (float)
- `narrative_summary`: object (multi-moment only) with `moments_count`, `role_order`, `per_role_duration`, `total_gap_seconds`
