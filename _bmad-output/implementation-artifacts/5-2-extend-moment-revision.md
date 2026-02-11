---
status: done
story: 5.2
epic: 5
title: "Extend Moment Revision"
completedAt: "2026-02-11"
---

# Story 5.2: Extend Moment Revision

## Implementation Notes

- `RevisionHandler._extend_moment()` reads moment-selection.json, adjusts timestamps
- Widens clip by `extra_seconds` (default 15s) before and after
- Clamps start_seconds to 0.0 minimum
- Writes revised moment to `moment-selection-revised.json`
- All file I/O via `asyncio.to_thread` (non-blocking)
- Exception chaining with `RevisionError` for JSON/IO failures
- Re-runs: FFmpeg → Assembly → Delivery
