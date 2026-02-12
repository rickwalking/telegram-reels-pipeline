# Stage 6: FFmpeg Engineering

## Objective

Plan FFmpeg crop and encode operations to convert source video segments into vertical 9:16 format at target specifications. Use face position data and quality checks to ensure no speakers are cut off and visual quality is maintained. The agent plans commands; the FFmpegAdapter executes them.

## Inputs

- **layout-analysis.json**: Contains `segments` with layout names, crop regions, quality predictions, and `speaker_face_mapping`
- **face-position-map.json**: Per-frame face positions and speaker position summary
- **speaker-timeline.json**: Speaker turn boundaries (used to verify active speaker alignment)
- **moment-selection.json**: Contains overall `start_seconds`, `end_seconds`
- **Video file path**: Source video for encoding

## Expected Outputs

- **encoding-plan.json**: FFmpeg command specifications with face validation and quality results
- **Encoded segment files**: segment-001.mp4, segment-002.mp4, etc.

```json
{
  "commands": [
    {
      "input": "/workspace/runs/XYZ/source.mp4",
      "crop_filter": "crop=960:1080:0:0,scale=1080:1920:flags=lanczos",
      "output": "/workspace/runs/XYZ/segment-001.mp4",
      "start_seconds": 1247.0,
      "end_seconds": 1268.0,
      "validation": {
        "face_in_crop": true,
        "face_source": "Speaker_Left",
        "active_speaker": "A"
      },
      "quality": {
        "upscale_factor": 1.125,
        "quality": "good",
        "recommendation": "proceed"
      }
    }
  ],
  "segment_paths": ["/workspace/runs/XYZ/segment-001.mp4"],
  "total_duration_seconds": 78
}
```

## Responsibilities

The FFmpeg Engineer **plans** encoding commands. The FFmpegAdapter **executes** them. After execution, the FFmpeg Engineer **validates** results.

- **Planning phase** (steps 1-9): Produce `encoding-plan.json` with all FFmpeg command specifications.
- **Execution phase**: FFmpegAdapter runs the planned commands.
- **Validation phase** (steps 10-13): Run post-encode quality and face checks. Update `encoding-plan.json` with results.

## Instructions

### Planning Phase

1. **Read layout analysis** to get segment boundaries, sub-segments, crop regions, and `speaker_face_mapping`.

2. **Read face-position-map.json** to understand scene composition and verify face positions.

3. **For each segment (or sub-segment)**, verify the proposed crop region contains a face by checking `face-position-map.json` at the segment's timestamps. The proposed crop area must overlap with a detected face. If no face in range, adjust the crop to center on the **active speaker's face** (use `speaker_face_mapping` from `layout-analysis.json` to preserve speaker identity — do NOT snap to the nearest arbitrary face).

4. **Build crop filter** for each segment: `crop={width}:{height}:{x}:{y},scale=1080:1920:flags=lanczos`. See `crop-playbook.md`.
   - **Always use `flags=lanczos`** in scale filters (sharper than default bicubic, no performance penalty).

5. **Handle quality degradation** for segments flagged by the Layout Detective:
   - For `quality: "degraded"` (upscale 1.5-2.0x): try widening the crop to include more background around the face while keeping face centered. Recheck upscale factor.
   - For `quality: "unacceptable"` (upscale > 2.0x): **use pillarbox mode**: `scale=-1:1920:flags=lanczos,pad=1080:1920:(1080-iw)/2:0:black`

6. **Set encoding parameters** per `encoding-params.md`: H.264 Main, CRF 23, preset medium.

7. **Handle transitions** — split at layout boundaries, encode each sub-segment separately. Add **0.5s overlap** at transition points for smooth concatenation (the Assembly stage trims the overlap).

8. **Validate crop coordinates** — ensure they don't exceed source video dimensions.

9. **Number segments sequentially**: segment-001.mp4, segment-002.mp4, etc. Output `encoding-plan.json`.

### Validation Phase (after FFmpegAdapter executes)

10. **Run quality check** on each encoded segment using the `representative_frame` from `layout-analysis.json`:
    ```bash
    python scripts/check_upscale_quality.py <segment.mp4> --crop-width <W> --target-width 1080 --source-frame <representative_frame.png>
    ```
    Update `encoding-plan.json` with quality results under the `quality` key per command.

11. **Include face validation results** in `encoding-plan.json` under the `validation` key per command.

12. **Safety net**: If the crop area at a segment's timestamps has 0 detected faces in `face-position-map.json`, flag for rework. Something went wrong with crop computation.

13. **Update `encoding-plan.json`** with final validation and quality data.

## Constraints

- Output dimensions: 1080x1920 (9:16 vertical)
- Codec: H.264 Main profile, CRF 23
- Scaler: **lanczos** (mandatory for all scale filters)
- Peak memory: < 3GB (NFR-P4)
- Encoding time: < 5 minutes per 90s segment on Pi ARM (NFR-P2)
- File size target: < 50MB per segment
- Crop coordinates must be within source bounds
- Pillarbox required when upscale factor > 2.0x
- All segments must have face validation results in encoding-plan.json

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/ffmpeg-criteria.md`

## Escalation Rules

- Encoding repeatedly fails → reduce preset to "fast" and retry
- Memory exceeds limit → split segment and encode in parts
- Source video is corrupt or unreadable → fail stage with error details
- Segment has 0 faces in crop region → flag for rework (adjust crop to include face)

## Prior Artifact Dependencies

- `layout-analysis.json` from Stage 5 (Layout Detective) — segment layouts, sub-segments, crop regions, speaker_face_mapping
- `face-position-map.json` from Stage 5 (Layout Detective) — face positions for validation
- `speaker-timeline.json` from Stage 5 (Layout Detective) — speaker turn boundaries for active speaker verification
- `moment-selection.json` from Stage 3 (Transcript) — overall timestamp range
- Source video file from Stage 2 (Research)
