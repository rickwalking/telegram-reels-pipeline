# Story 17-1: Veo3 Domain Models

## Context

Epic 11 (Story 11-1) introduced a minimal `Veo3Prompt(variant: str, prompt: str)` frozen dataclass and added `veo3_prompts: tuple[Veo3Prompt, ...]` to `PublishingAssets` in `domain/models.py`. This story extends `Veo3Prompt` with three new fields needed for the Veo3 B-roll integration: `narrative_anchor` (story-language placement hint), `duration_s` (director-specified clip length), and `idempotent_key` (deterministic deduplication key). It also introduces two new domain models — `Veo3JobStatus` enum and `Veo3Job` frozen dataclass — to represent generation job lifecycle state.

All models follow existing domain conventions: frozen dataclasses, `tuple` not `list`, `Mapping` + `MappingProxyType` not `dict`, stdlib only (no Pydantic in domain).

## Story

As a pipeline developer,
I want to extend the existing `Veo3Prompt` frozen dataclass and add new `Veo3Job` and `Veo3JobStatus` models,
so that the domain layer can represent Veo3 generation state and editorial intent without external dependencies.

## Acceptance Criteria

1. Given the existing `Veo3Prompt(variant, prompt)` in `domain/models.py`, when the dataclass is extended, then three new fields are added: `narrative_anchor: str`, `duration_s: int`, `idempotent_key: str` — preserving frozen + tuple conventions

2. Given the extended `Veo3Prompt`, when `__post_init__` validation runs, then `duration_s` must be between 5 and 8 (inclusive), `variant` must be one of `intro`, `broll`, `outro`, `transition`, and `idempotent_key` must be non-empty

3. Given the existing `PublishingAssets.veo3_prompts: tuple[Veo3Prompt, ...]`, when the extended `Veo3Prompt` is used, then the tuple type remains compatible (no changes to `PublishingAssets` needed)

4. Given the domain layer, when `Veo3JobStatus` is defined, then it is an enum with values: `PENDING`, `GENERATING`, `COMPLETED`, `FAILED`, `TIMED_OUT`

5. Given the domain layer, when `Veo3Job` is defined, then it is a frozen dataclass with fields: `idempotent_key: str`, `variant: str`, `prompt: str`, `status: Veo3JobStatus`, `video_path: str | None`, `error_message: str | None`

6. Given variant taxonomy constants, when referenced, then `intro`, `broll`, `outro`, `transition` are available as string constants (e.g., `VEO3_VARIANT_INTRO = "intro"`)

7. Given a run_id and variant, when an idempotent key is generated, then the pattern is `{run_id}_{variant}` — deterministic with zero collision risk

## Tasks

- [ ] Task 1: Extend `Veo3Prompt` in `domain/models.py` with `narrative_anchor`, `duration_s`, `idempotent_key` fields
- [ ] Task 2: Add `__post_init__` validation for duration range, variant values, non-empty key
- [ ] Task 3: Add `Veo3JobStatus` enum after `Veo3Prompt`
- [ ] Task 4: Add `Veo3Job` frozen dataclass after `Veo3JobStatus`
- [ ] Task 5: Add variant taxonomy constants (`VEO3_VARIANT_INTRO`, etc.)
- [ ] Task 6: Add helper function `make_idempotent_key(run_id: str, variant: str) -> str`
- [ ] Task 7: Unit tests for extended Veo3Prompt construction, immutability, validation
- [ ] Task 8: Unit tests for Veo3Job construction and status transitions
- [ ] Task 9: Unit tests for idempotent key generation

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/models.py` | Extend existing `Veo3Prompt` with 3 new fields, add `Veo3JobStatus` enum, add `Veo3Job` dataclass, add variant constants | Domain model |
| `tests/unit/domain/test_veo3_models.py` | New file — Veo3Prompt extension, Veo3Job, validation, idempotent key tests | Tests |

## Technical Notes

- This extends an EXISTING dataclass — do not create a duplicate. The `Veo3Prompt` at line ~261 of `domain/models.py` gets new fields added
- Frozen dataclasses cannot have mutable defaults. Use `None` for optional fields (`video_path`, `error_message`)
- The `make_idempotent_key()` helper is a pure function in the domain layer (no I/O)
- `variant` validation should use the taxonomy constants, not hardcoded strings
- Keep new models adjacent to existing `Veo3Prompt` and `PublishingAssets` in the file

## Definition of Done

- Extended `Veo3Prompt` with 3 new fields and validation
- `Veo3JobStatus` enum and `Veo3Job` frozen dataclass in domain layer
- Variant taxonomy constants and idempotent key helper
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
