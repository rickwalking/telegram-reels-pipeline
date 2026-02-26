# Story 20-2: Cutaway Manifest Domain Model

## Status: review

## Context

The pipeline currently uses `BrollPlacement` to represent resolved B-roll clip positions in the final reel timeline. This model is Veo3-specific (variant must match `Veo3PromptVariant`). As the pipeline evolves to support multiple clip sources (Veo3, external stock footage, user-provided clips), a unified `CutawayManifest` domain model is needed to represent all cutaway clips regardless of source, with overlap resolution and sorted ordering.

## Story

As a pipeline developer,
I want a unified CutawayManifest domain model that represents cutaway clips from any source with overlap resolution,
so that the assembly stage can handle mixed clip sources without source-specific logic.

## Acceptance Criteria

1. Given the domain layer, when `ClipSource` is defined, then it is a `StrEnum` with values: `veo3`, `external`, `user_provided`

2. Given the domain layer, when `CutawayClip` is defined, then it is a frozen dataclass with source, variant, clip_path, insertion_point_s, duration_s, narrative_anchor, match_confidence fields and validation

3. Given `CutawayClip`, when `end_s` property is accessed, then it returns `insertion_point_s + duration_s`

4. Given overlapping clips, when `resolve_overlaps()` is called, then the clip with higher `match_confidence` wins; ties are broken by source priority (user_provided > veo3 > external)

5. Given the domain layer, when `CutawayManifest` is defined, then it validates clips are sorted by `insertion_point_s`

6. Given `CutawayManifest.from_broll_and_external()`, when called with BrollPlacements and external clips, then it converts, merges, resolves overlaps, sorts, and returns (manifest, dropped_clips)

7. Given `ReelAssembler.assemble_with_broll()`, when called, then it accepts a `CutawayManifest` instead of raw `BrollPlacement` tuple

## Tasks

- [x] Task 1: Add `ClipSource` StrEnum to `domain/models.py`
- [x] Task 2: Add `CutawayClip` frozen dataclass with validation and `end_s` property
- [x] Task 3: Add `resolve_overlaps()` pure function with `_SOURCE_PRIORITY` dict
- [x] Task 4: Add `CutawayManifest` frozen dataclass with `from_broll_and_external()` factory
- [x] Task 5: Update `reel_assembler.assemble_with_broll()` to accept `CutawayManifest`
- [x] Task 6: Unit tests for all new domain models and overlap resolution
- [x] Task 7: Run full test suite, ruff, mypy — all pass

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/models.py` | Add `ClipSource`, `CutawayClip`, `resolve_overlaps()`, `CutawayManifest` | Domain model |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | Change `assemble_with_broll()` to accept `CutawayManifest` | Infrastructure adapter |
| `tests/unit/domain/test_cutaway_manifest.py` | New file — unit tests | Tests |
| `tests/unit/infrastructure/test_reel_assembler_broll.py` | Update calls to use `CutawayManifest` | Tests |

## Definition of Done

- `ClipSource` StrEnum, `CutawayClip` frozen dataclass, `resolve_overlaps()` pure function, `CutawayManifest` with factory in domain layer
- `assemble_with_broll()` accepts `CutawayManifest` and converts internally
- All tests pass (1364), ruff clean, mypy clean
- Min 80% coverage on new code
