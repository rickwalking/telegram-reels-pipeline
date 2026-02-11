# Stage 5: Layout Detection

## Objective

Extract video frames at regular intervals within the selected moment, classify each frame's camera layout, detect transitions, and produce crop strategies for vertical Reel conversion.

## Inputs

- **Video file**: Downloaded source video (typically 1920x1080)
- **moment-selection.json**: Contains `start_seconds`, `end_seconds` for frame extraction range
- **Known strategies**: From knowledge base (crop-strategies.yaml) for previously learned layouts

## Expected Outputs

- **layout-analysis.json**: Frame classifications and segment layout plan

```json
{
  "classifications": [
    {"timestamp": 1247.0, "layout_name": "side_by_side", "confidence": 0.95}
  ],
  "segments": [
    {
      "start_seconds": 1247.0, "end_seconds": 1325.0,
      "layout_name": "side_by_side",
      "crop_region": {"x": 0, "y": 0, "width": 960, "height": 1080}
    }
  ],
  "escalation_needed": false
}
```

**CRITICAL**: Layout names MUST be snake_case: `side_by_side`, `speaker_focus`, `grid`.

## Instructions

1. **Extract frames** every 5 seconds from `start_seconds` to `end_seconds` using VideoProcessingPort.
2. **Classify each frame** against known layouts. See `frame-analysis.md`.
3. **Check confidence** — frames with confidence < 0.7 may need escalation.
4. **Check knowledge base** before escalating — a previously learned strategy may apply.
5. **Detect transitions** — consecutive frames with different layouts mark segment boundaries.
6. **Group into segments** — contiguous same-layout frames become SegmentLayout entries.
7. **Assign crop regions** for each segment per `crop-playbook.md`.
8. **Escalate unknown layouts** per `escalation-protocol.md` if needed.
9. **Output valid JSON** as `layout-analysis.json`.

## Constraints

- Frame extraction interval: every 5 seconds within the moment
- Confidence threshold: 0.7 minimum for accepted classification
- Layout names must match KNOWN_LAYOUTS: `side_by_side`, `speaker_focus`, `grid` (snake_case)
- Crop regions must be within source video bounds (x + width <= 1920, y + height <= 1080)

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/layout-criteria.md`

## Escalation Rules

- Unknown layout detected → follow `escalation-protocol.md` (screenshot → user → learn)
- All frames unrecognized → escalate with representative frame
- Confidence < 0.5 → mandatory escalation regardless of knowledge base

## Prior Artifact Dependencies

- Source video file from Stage 2 (Research) — downloaded video
- `moment-selection.json` from Stage 3 (Transcript) — timestamp range for frame extraction
