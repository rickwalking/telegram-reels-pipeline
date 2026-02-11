---
status: done
story: 6.4
epic: 6
title: "Operations Tooling & Filesystem Inspection"
completedAt: "2026-02-11"
---

# Story 6.4: Operations Tooling & Filesystem Inspection

## Implementation Notes

- `RunCleaner` application component with configurable retention period (default 30 days)
- Scans `workspace/runs/` for old run directories based on `run.md` mtime
- Preserves: `run.md` metadata, `events.log` timeline, `.mp4` final Reels
- Removes: intermediate artifacts (frames, transcripts, content JSON, segment videos)
- Cleans up empty subdirectories after artifact removal
- Security: skips symlinked run directories, validates resolved-path containment
- All file I/O wrapped in `asyncio.to_thread`
- `CleanupResult` frozen dataclass: `runs_scanned`, `runs_cleaned`, `bytes_freed`
- Run directory structure (from existing infra): `{run_id}/run.md`, `{run_id}/events.log`, artifacts
- Knowledge base at `config/crop-strategies.yaml` (from Epic 3, already human-readable)
