# Stage 7: Assembly

## Objective

Combine encoded video segments into the final Instagram Reel, verify quality, and prepare for delivery.

## Inputs

- **Encoded segment files**: segment-001.mp4, segment-002.mp4, etc. from Stage 6
- **encoding-plan.json**: Contains `segment_paths`, `total_duration_seconds`, and optional `style_transitions` journal
- **moment-selection.json**: Expected duration for validation

## Expected Outputs

- **final-reel.mp4**: The assembled final video
- **assembly-report.json**: Assembly plan and quality verification

```json
{
  "concatenation_order": ["segment-001.mp4", "segment-002.mp4"],
  "transitions": [{"type": "cut", "at_seconds": 10.0}],
  "final_output_path": "/workspace/runs/XYZ/final-reel.mp4",
  "quality_checks": {
    "dimensions": "1080x1920",
    "duration_seconds": 78,
    "file_size_mb": 42,
    "codec": "h264",
    "audio_codec": "aac",
    "all_segments_valid": true,
    "duration_within_tolerance": true
  },
  "style_summary": {
    "framing_style": "auto",
    "transitions_count": 3,
    "states_used": ["solo", "duo_split", "screen_share"],
    "effects_applied": ["focus_pull", "spotlight_dim"]
  }
}
```

## Instructions

1. **Verify all segments exist** and are readable. List any missing segments.
2. **Validate each segment**: check dimensions (1080x1920), codec (H.264), audio (AAC).
3. **Determine concatenation order**:
   - **Single-moment mode**: sequential by segment number.
   - **Multi-moment mode**: reorder segments from chronological I/O order (how they were encoded) into **narrative role order** (intro → buildup → core → reaction → conclusion). Use the `moment_index` and `narrative_role` fields from `encoding-plan.json` commands to group and sort.
4.5. **Discover B-roll clips** — if a `veo3/` folder exists in the workspace, read `veo3/jobs.json` for completed clips. Use the B-roll placer to resolve insertion points based on variant type and narrative anchors. Include B-roll details in the assembly report.
4. **Plan transitions** — check `encoding-plan.json` for `style_transitions`. Use the `transition_kind` field to select transition type:
   - `style_change`: 0.5s slide effect (within-moment style transitions)
   - `narrative_boundary`: 1.0s dissolve effect (between-moment transitions)
   - If no transitions exist, use hard cuts (`-c copy` concat).
5. **Execute concatenation** via ReelAssembler adapter. Pass `TransitionSpec` tuples for xfade mode, or omit for concat mode. If xfade fails, fall back to hard-cut concat and log warning.
6. **Validate final output**: dimensions, duration, file size, codec.
7. **Account for boundary trims** — if `encoding-plan.json` contains segments with `boundary_validation` entries where `start_trimmed` or `end_trimmed` is true, subtract the total trimmed seconds from the expected duration before checking tolerance. Log trimmed gaps in `assembly-report.json` under a `boundary_trims` key listing each trim with its timestamp and duration.
8. **Check duration tolerance**: final duration should be within the appropriate tolerance of the trim-adjusted expected duration:
   - **Single-moment**: within 5% of expected
   - **Multi-moment**: within 15% of `target_duration_seconds` (wider tolerance accounts for transition overlaps and per-moment boundary trims)
9. **Summarize style transitions** — if `encoding-plan.json` contains `style_transitions`, include a `style_summary` in `assembly-report.json` with: `framing_style` used, `transitions_count`, unique `states_used`, and `effects_applied`.
10. **Summarize narrative structure** (multi-moment only) — include a `narrative_summary` in `assembly-report.json` with: `moments_count`, `role_order` (list of roles in final assembly order), `per_role_duration` (object mapping role to screen time in seconds), and `total_gap_seconds` (total time between non-contiguous moments in source video).
11. **Output assembly-report.json** with quality verification results, style summary, and narrative summary.

## Constraints

- Final dimensions: 1080x1920
- Duration tolerance: within 5% of expected (from moment-selection.json)
- All segments must have matching encoding parameters (codec, resolution, audio)
- File size noted for delivery routing (< 50MB = inline, >= 50MB = Google Drive)

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/assembly-criteria.md`

## Escalation Rules

- Missing segments → fail with details of which segments are missing
- Dimension mismatch → fail with the specific segment's actual dimensions
- Duration mismatch > 10% → fail, suggest checking segment order
- Corrupt output → fail with probe error details

## Prior Artifact Dependencies

- Encoded segments from Stage 6 (FFmpeg Engineer)
- `encoding-plan.json` from Stage 6 — segment paths and expected duration
- `moment-selection.json` from Stage 3 (Transcript) — expected total duration. Multi-moment: `moments[]` array for narrative reordering and per-role duration reporting
