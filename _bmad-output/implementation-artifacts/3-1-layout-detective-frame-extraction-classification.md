---
status: done
story: 3.1
epic: 3
title: "Layout Detective — Frame Extraction & Classification"
completedAt: "2026-02-11"
---

# Story 3.1: Layout Detective — Frame Extraction & Classification

## Implementation Notes

- Created `FFmpegAdapter` implementing `VideoProcessingPort` with `extract_frames()` using FFmpeg subprocess
- Created `layout_classifier.py` with `parse_layout_classifications()` and `group_into_segments()`
- Added `LayoutClassification` and `SegmentLayout` frozen dataclasses to domain models
- Updated `VideoProcessingPort` to use `SegmentLayout` in `crop_and_encode` signature
- `group_into_segments` handles noisy classifier output: sorts, deduplicates, clamps timestamps
- Known layouts: `side_by_side`, `speaker_focus`, `grid`; others trigger escalation
- 30+ tests covering parsing, grouping, edge cases (duplicates, out-of-range timestamps)
