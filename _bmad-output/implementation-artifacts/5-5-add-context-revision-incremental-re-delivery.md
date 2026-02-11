---
status: done
story: 5.5
epic: 5
title: "Add Context Revision & Incremental Re-Delivery"
completedAt: "2026-02-11"
---

# Story 5.5: Add Context Revision & Incremental Re-Delivery

## Implementation Notes

- `RevisionHandler._add_context()` widens timestamp window by `extra_seconds` (default 30s)
- Sets `context_added: true` and `user_instruction` in revised moment file
- `RevisionResult.stages_rerun` tracks which stages were re-run for incremental delivery
- Delivery stage only sends changed output based on `stages_rerun` tuple
- All file I/O via `asyncio.to_thread` with exception chaining
- Re-runs: FFmpeg → Assembly → Delivery
