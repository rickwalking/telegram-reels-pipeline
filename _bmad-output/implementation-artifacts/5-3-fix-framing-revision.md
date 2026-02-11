---
status: done
story: 5.3
epic: 5
title: "Fix Framing Revision"
completedAt: "2026-02-11"
---

# Story 5.3: Fix Framing Revision

## Implementation Notes

- `RevisionHandler._fix_framing()` reads layout-segments.json, marks target segment
- Sets `needs_reframe: true` and `user_instruction` on the target segment
- Writes revised layout to `layout-segments-revised.json`
- Target segment validated >= 0 at domain model level
- All file I/O via `asyncio.to_thread` with exception chaining
- Re-runs: FFmpeg → Assembly → Delivery
