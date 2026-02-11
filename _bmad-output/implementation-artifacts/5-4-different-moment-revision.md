---
status: done
story: 5.4
epic: 5
title: "Different Moment Revision"
completedAt: "2026-02-11"
---

# Story 5.4: Different Moment Revision

## Implementation Notes

- `RevisionHandler._different_moment()` creates a `revision-hint.json` file
- Includes optional `timestamp_hint` for targeted moment search
- Triggers full downstream re-processing: Transcript → Content → Layout → FFmpeg → Assembly → Delivery
- Creates assets directory if needed
- All file I/O via `asyncio.to_thread`
