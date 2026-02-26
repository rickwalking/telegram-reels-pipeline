# Story 20-2: Cutaway Manifest Domain Model

## Context

Currently the reel assembler accepts `tuple[BrollPlacement, ...]` for B-roll overlay. With Story 20-1's external clip downloader in place, we need a unified domain model that can represent clips from multiple sources (Veo3, external downloads, user-provided). The `CutawayManifest` merges all clip sources into a single sorted list for the assembly engine.

**Key design decisions from Codex review:**
- Overlap detection is a **pure domain function** (no I/O, no logging side effects) — returns `(kept, dropped)` tuple; caller handles logging
- Tie-break priority: `user_provided` > `veo3` > `external`
- `CutawayClip.source` uses a `StrEnum` for type safety

## Story

As a pipeline developer,
I want a unified `CutawayManifest` domain model that merges Veo3 and external clips into a single ordered list,
so that the assembly engine has one consistent interface regardless of clip source.

## Acceptance Criteria

1. Given the domain layer, when `CutawayClip` is defined, then it is a frozen dataclass with fields: `source` (enum), `variant`, `clip_path`, `insertion_point_s`, `duration_s`, `narrative_anchor`, `match_confidence`

2. Given `ClipSource`, when defined, then it is a StrEnum with values: `veo3`, `external`, `user_provided`

3. Given `CutawayManifest`, when defined, then it is a frozen dataclass with `clips: tuple[CutawayClip, ...]` ordered by `insertion_point_s`

4. Given a factory method, when merging B-roll and external clips, then `CutawayManifest.from_broll_and_external()` merges, sorts by insertion time, and detects overlaps

5. Given two overlapping clips, when resolved, then the one with higher `match_confidence` wins; on tie, source priority is `user_provided` > `veo3` > `external`

6. Given overlap resolution, when computed, then it is a pure function returning `(kept: tuple[CutawayClip, ...], dropped: tuple[CutawayClip, ...])` — no logging in domain

7. Given `reel_assembler.assemble_with_broll()`, when updated, then it accepts `CutawayManifest` instead of `tuple[BrollPlacement, ...]`

8. Given backward compatibility, when `BrollPlacement` is used, then it converts to `CutawayClip` with `source=ClipSource.VEO3`

## Tasks

- [ ] Task 1: Add `ClipSource` StrEnum to `domain/models.py`
  - [ ] Subtask 1a: Values: `VEO3 = "veo3"`, `EXTERNAL = "external"`, `USER_PROVIDED = "user_provided"`
  - [ ] Subtask 1b: Place after `BrollPlacement` class
- [ ] Task 2: Add `CutawayClip` frozen dataclass to `domain/models.py`
  - [ ] Subtask 2a: Fields: `source: ClipSource`, `variant: str`, `clip_path: str`, `insertion_point_s: float`, `duration_s: float`, `narrative_anchor: str`, `match_confidence: float`
  - [ ] Subtask 2b: `__post_init__` validation: positive duration, confidence 0.0-1.0, non-empty clip_path
  - [ ] Subtask 2c: Add `end_s` property: `insertion_point_s + duration_s`
- [ ] Task 3: Add overlap resolution pure function
  - [ ] Subtask 3a: `def resolve_overlaps(clips: tuple[CutawayClip, ...]) -> tuple[tuple[CutawayClip, ...], tuple[CutawayClip, ...]]` — returns `(kept, dropped)`
  - [ ] Subtask 3b: Two clips overlap if `clip_a.insertion_point_s < clip_b.end_s and clip_b.insertion_point_s < clip_a.end_s`
  - [ ] Subtask 3c: Winner: higher `match_confidence`; tie-break by `_SOURCE_PRIORITY = {USER_PROVIDED: 0, VEO3: 1, EXTERNAL: 2}`
  - [ ] Subtask 3d: Pure function — no I/O, no logging, no side effects
- [ ] Task 4: Add `CutawayManifest` frozen dataclass
  - [ ] Subtask 4a: Fields: `clips: tuple[CutawayClip, ...]`
  - [ ] Subtask 4b: `__post_init__` validation: clips sorted by `insertion_point_s`
  - [ ] Subtask 4c: Factory method `from_broll_and_external(broll, external)` → merges, resolves overlaps, sorts
  - [ ] Subtask 4d: Conversion helper: `BrollPlacement` → `CutawayClip(source=ClipSource.VEO3, ...)`
- [ ] Task 5: Update `reel_assembler.assemble_with_broll()` to accept `CutawayManifest`
  - [ ] Subtask 5a: Change parameter from `broll_placements: tuple[BrollPlacement, ...]` to `manifest: CutawayManifest`
  - [ ] Subtask 5b: Extract `BrollPlacement`-compatible data from `CutawayClip` for overlay
  - [ ] Subtask 5c: Update all callers of `assemble_with_broll()` (search codebase)
- [ ] Task 6: Unit tests
  - [ ] Subtask 6a: Test `CutawayClip` construction, validation, immutability
  - [ ] Subtask 6b: Test `resolve_overlaps()` — no overlaps (pass-through), two overlapping (higher confidence wins), tie-break by source priority
  - [ ] Subtask 6c: Test `CutawayManifest.from_broll_and_external()` — merge, sort, overlap resolution
  - [ ] Subtask 6d: Test `BrollPlacement` → `CutawayClip` conversion
  - [ ] Subtask 6e: Test manifest ordering validation
- [ ] Task 7: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Domain (`models.py`) for models + pure functions; Infrastructure (`reel_assembler.py`) for updated API
- **Domain purity:** `resolve_overlaps()` is a pure function — no logging, no I/O. Callers (application layer) handle logging of dropped clips
- **Frozen dataclass conventions:** `tuple` not `list`, `Mapping` + `MappingProxyType` not `dict`

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/domain/models.py` | 579-600 | `BrollPlacement` — existing model to extend from |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 291-338 | `assemble_with_broll()` — update parameter type |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 213-289 | `_overlay_broll()` — reads clip_path, insertion_point_s, duration_s |
| `tests/unit/infrastructure/test_reel_assembler_broll.py` | — | Existing tests to update for new parameter type |

### Source Priority Constants

```python
_SOURCE_PRIORITY: dict[ClipSource, int] = {
    ClipSource.USER_PROVIDED: 0,  # Highest
    ClipSource.VEO3: 1,
    ClipSource.EXTERNAL: 2,      # Lowest
}
```

## Definition of Done

- `ClipSource`, `CutawayClip`, `CutawayManifest` in domain layer
- Pure `resolve_overlaps()` function with tie-break
- `assemble_with_broll()` accepts `CutawayManifest`
- Backward compatible via `BrollPlacement` → `CutawayClip` conversion
- All tests pass, linters clean, mypy clean
- Min 80% coverage on changed code

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log

## Status

ready-for-dev
