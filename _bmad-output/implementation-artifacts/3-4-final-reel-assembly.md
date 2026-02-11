---
status: done
story: 3.4
epic: 3
title: "Final Reel Assembly"
completedAt: "2026-02-11"
---

# Story 3.4: Final Reel Assembly

## Implementation Notes

- `ReelAssembler` concatenates encoded segments into a single reel via FFmpeg concat demuxer
- Single segment: file copy (no re-encoding). Multiple: FFmpeg concat with stream copy
- `validate_duration()` via ffprobe checks 30-120s bounds (configurable)
- Concat list file paths escaped for safety, cleaned up in `finally` block
- Output directory created automatically
- `FFmpegAdapter.concat_videos()` also available for general-purpose concatenation
- 12+ tests covering single/multi segment, duration validation, error handling, cleanup
