# Stage 6: FFmpeg Engineering

## Objective

Plan FFmpeg crop and encode operations to convert source video segments into vertical 9:16 format at target specifications. The agent plans commands; the FFmpegAdapter executes them.

## Inputs

- **layout-analysis.json**: Contains `segments` with layout names and crop regions
- **moment-selection.json**: Contains overall `start_seconds`, `end_seconds`
- **Video file path**: Source video for encoding

## Expected Outputs

- **encoding-plan.json**: FFmpeg command specifications
- **Encoded segment files**: segment-001.mp4, segment-002.mp4, etc.

```json
{
  "commands": [
    {
      "input": "/workspace/runs/XYZ/source.mp4",
      "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
      "output": "/workspace/runs/XYZ/segment-001.mp4",
      "start_seconds": 1247.0,
      "end_seconds": 1325.0
    }
  ],
  "segment_paths": ["/workspace/runs/XYZ/segment-001.mp4"],
  "total_duration_seconds": 78
}
```

## Instructions

1. **Read layout analysis** to get segment boundaries and crop regions.
2. **Build crop filter** for each segment: `crop={width}:{height}:{x}:{y},scale=1080:1920`. See `crop-playbook.md`.
3. **Set encoding parameters** per `encoding-params.md`: H.264 Main, CRF 23, preset medium.
4. **Handle transitions** — split at layout boundaries, encode each sub-segment separately.
5. **Validate crop coordinates** — ensure they don't exceed source video dimensions.
6. **Number segments sequentially**: segment-001.mp4, segment-002.mp4, etc.
7. **Output valid JSON** as `encoding-plan.json`.

## Constraints

- Output dimensions: 1080x1920 (9:16 vertical)
- Codec: H.264 Main profile, CRF 23
- Peak memory: < 3GB (NFR-P4)
- Encoding time: < 5 minutes per 90s segment on Pi ARM (NFR-P2)
- File size target: < 50MB per segment
- Crop coordinates must be within source bounds

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/ffmpeg-criteria.md`

## Escalation Rules

- Encoding repeatedly fails → reduce preset to "fast" and retry
- Memory exceeds limit → split segment and encode in parts
- Source video is corrupt or unreadable → fail stage with error details

## Prior Artifact Dependencies

- `layout-analysis.json` from Stage 5 (Layout Detective) — segment layouts and crop regions
- `moment-selection.json` from Stage 3 (Transcript) — overall timestamp range
- Source video file from Stage 2 (Research)
