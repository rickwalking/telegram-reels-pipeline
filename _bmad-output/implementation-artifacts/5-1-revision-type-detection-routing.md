---
status: done
story: 5.1
epic: 5
title: "Revision Type Detection & Routing"
completedAt: "2026-02-11"
---

# Story 5.1: Revision Type Detection & Routing

## Implementation Notes

- Created `revision_router.py` in application layer with `RevisionRouter`
- Uses `ModelDispatchPort` to classify user messages into `RevisionType` enum
- Parsing functions (`parse_revision_classification`, `parse_timestamp_hint`, `parse_extra_seconds`) live in application layer (pure functions)
- Falls back to clarifying question via `MessagingPort` when confidence < 0.7 threshold
- User can confirm, select by number, or type revision name
- Added `RevisionRequest` and `RevisionResult` frozen dataclasses to domain models
- Validates `target_segment >= 0` in `RevisionRequest.__post_init__`
- 25+ tests covering classification, clarification, prompt building
