# Stage 5: Layout Detection

## Objective

Extract video frames at regular intervals within the selected moment, run face detection to map all speaker positions, parse VTT for speaker timing, classify each frame's camera layout, detect transitions, and produce face-centered crop strategies for vertical Reel conversion.

## Inputs

- **Video file**: Downloaded source video (typically 1920x1080)
- **moment-selection.json**: Contains `start_seconds`, `end_seconds` for frame extraction range
- **VTT subtitle file**: Raw VTT from YouTube (already downloaded in Stage 2)
- **Known strategies**: From knowledge base (crop-strategies.yaml) for previously learned layouts

## Expected Outputs

- **face-position-map.json**: Per-frame face positions and speaker position summary
- **speaker-timeline.json**: Speaker turn boundaries from VTT markers
- **layout-analysis.json**: Frame classifications and segment layout plan with face-centered crops

```json
{
  "classifications": [
    {"timestamp": 1247.0, "layout_name": "side_by_side", "confidence": 0.95}
  ],
  "speaker_face_mapping": {
    "A": "Speaker_Left",
    "B": "Speaker_Right"
  },
  "segments": [
    {
      "start_seconds": 1247.0, "end_seconds": 1290.0,
      "layout_name": "side_by_side",
      "representative_frame": "frame_1260.png",
      "crop_region": {"x": 180, "y": 0, "width": 960, "height": 1080}
    }
  ],
  "escalation_needed": false,
  "quality_predictions": [
    {"segment": 0, "crop_width": 960, "upscale_factor": 1.125, "quality": "good"}
  ]
}
```

**Note**: `side_by_side` segments use `sub_segments` ONLY when speakers are too far apart for a single crop. When both speakers fit in one crop (`speaker_span <= crop_width - 80`), use a single `crop_region` at the segment level — same as `speaker_focus`.

**CRITICAL**: Layout names MUST be snake_case: `side_by_side`, `speaker_focus`, `grid`.

## Instructions

1. **Extract frames** every 5 seconds from `start_seconds` to `end_seconds` using VideoProcessingPort. This is the **coarse pass** — it identifies approximate layout transition zones.

2. **Run face detection** on all extracted frames:
   ```bash
   python scripts/detect_faces.py <frames_dir> --output <workspace>/face-position-map.json
   ```
   This maps all face positions across every frame BEFORE any crop decisions.

3. **Run VTT speaker parser** on the subtitle file:
   ```bash
   python scripts/parse_vtt_speakers.py <vtt_file> --start-s <start> --end-s <end> --output <workspace>/speaker-timeline.json
   ```
   This identifies WHO talks WHEN from YouTube's speaker change markers.

4. **Read face-position-map.json summary**. Note `person_count`, `speaker_positions`, and `positions_stable`.

5. **Build speaker-to-face mapping** (required when both artifacts exist):
   - For each speaker turn in `speaker-timeline.json`, check which face positions are active at that timestamp in `face-position-map.json`
   - If Speaker A starts at t=1965 and only `Speaker_Left` has a face at nearby frames → `A = Speaker_Left`
   - Store mapping in `layout-analysis.json` as `speaker_face_mapping: {"A": "Speaker_Left", "B": "Speaker_Right"}`
   - If mapping is ambiguous (multiple faces at speaker start), note lower confidence but produce best-effort mapping

6. **Classify each frame** against known layouts using face data. See `frame-analysis.md`.

7. **Check confidence** — frames with confidence < 0.7 may need escalation.

8. **Check knowledge base** before escalating — a previously learned strategy may apply.

9. **Detect transitions** — consecutive frames with different layouts OR face count changes mark candidate transition zones.

10. **Refine transition boundaries** (fine pass) — for each candidate transition between frames at `T1` and `T2`:
    - Extract additional frames at 1-second intervals within `[T1, T2]` (e.g., if coarse frames at t=1776 and t=1781 differ, extract frames at t=1777, t=1778, t=1779, t=1780).
    - Run face detection on these new frames.
    - Identify the **first frame** that matches the new layout. Its timestamp is `T_precise`.
    - Use `T_precise` as the segment boundary instead of the midpoint `(T1 + T2) / 2`.
    - This eliminates the 1-3 second misalignment that causes wrong crops at camera cuts.

11. **Group into segments** — contiguous same-layout frames become SegmentLayout entries.

12. **Assign face-centered crop regions** for each segment per `crop-playbook.md`:
    - For `side_by_side` segments: **first check if both speakers fit in a single crop**:
      - Compute `speaker_span = rightmost_face_edge - leftmost_face_edge` (face x + face width for each speaker)
      - If `speaker_span <= 960 - 80` (880px): use ONE centered crop covering both speakers. Set `crop_region` at segment level (no `sub_segments`). The wide shot is meant to show both people — do NOT isolate one.
      - **Center the crop on the speakers**: `crop_x = speaker_center - crop_width / 2`. Do NOT offset the crop toward one side. Both speakers should have roughly equal margin.
      - If speakers are too far apart: produce `sub_segments` with minimum 5-second duration. Merge short speaker turns (< 5s) into the preceding sub_segment.
    - For `speaker_focus`: use the face centroid from `face-position-map.json` as the crop x offset. **Never hardcode x=280**.
    - For `grid`: map active speaker from timeline to the quadrant containing their face.
    - Include `representative_frame` path for each segment (used by Stage 6 for post-encode quality checks).

13. **Predict upscale quality** for each proposed crop:
    ```bash
    python scripts/check_upscale_quality.py --predict --crop-width <W> --target-width 1080
    ```
    Flag segments with `quality: "degraded"` or `"unacceptable"`. Include predictions in `layout-analysis.json`.

14. **Escalate unknown layouts** per `escalation-protocol.md` if needed.

15. **Output valid JSON** as `layout-analysis.json`.

## Fallback Behavior

| Scenario | Action |
|----------|--------|
| VTT has `>>` markers | Produce `speaker-timeline.json` with speaker turns. Build speaker-to-face mapping. |
| VTT has NO `>>` markers | `speaker-timeline.json` has `confidence: "none"`. Use both-visible centered crop if faces fit; otherwise alternate every 5-8 seconds. |
| No VTT file at all | Skip VTT parsing. Use face-position-based alternation. Note in `layout-analysis.json`. |
| `person_count: 0` (no faces) | Layout-based heuristic crops. Flag as lower confidence. QA will flag REWORK. |
| Detector error / no OpenCV | Skip face detection. Use layout defaults. QA will flag missing `face-position-map.json` as REWORK. |
| One face only | Use that face's position for entire segment. No alternation needed. |

## Constraints

- Frame extraction interval: every 5 seconds within the moment
- Confidence threshold: 0.7 minimum for accepted classification
- Layout names must match KNOWN_LAYOUTS: `side_by_side`, `speaker_focus`, `grid` (snake_case)
- Crop regions must be within source video bounds (x + width <= 1920, y + height <= 1080)
- Maximum 3 crop-switch cuts in any 15-second window
- Minimum sub-segment duration: 5 seconds (merge shorter turns into preceding segment)
- Face-centered crops required when face-position-map.json has face data
- Prefer both-visible centered crops for side_by_side over per-speaker isolation

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/layout-criteria.md`

## Escalation Rules

- Unknown layout detected → follow `escalation-protocol.md` (screenshot → user → learn)
- All frames unrecognized → escalate with representative frame
- Confidence < 0.5 → mandatory escalation regardless of knowledge base

## Prior Artifact Dependencies

- Source video file from Stage 2 (Research) — downloaded video
- VTT subtitle file from Stage 2 (Research) — raw VTT with speaker change markers
- `moment-selection.json` from Stage 3 (Transcript) — timestamp range for frame extraction
