---
status: done
story: 3.2
epic: 3
title: "FFmpeg Engineer — Crop & Encode"
completedAt: "2026-02-11"
---

# Story 3.2: FFmpeg Engineer — Crop & Encode

## Implementation Notes

- `FFmpegAdapter.crop_and_encode()` applies per-segment CropRegion for vertical 9:16 at 1080x1920
- Single segment: direct encode. Multiple segments: encode each then concat via FFmpeg demuxer
- Configurable thread count (`_DEFAULT_THREADS=2` for Pi, constructor param)
- `-vf crop=W:H:X:Y,scale=1080:1920` filter chain per segment
- Concat list file paths are properly escaped (single quotes) for safety
- Output directory created automatically if missing
- Temp segment files cleaned up in `finally` block
- `probe_duration()` via ffprobe for validation
- 15+ tests covering single/multi segment, filter format, thread config, error cases
