# Story 16-1: NarrativePlan Domain Model & Parser

## Context

Epic 14 introduced `NarrativeMoment` (frozen dataclass with `start_seconds`, `end_seconds`, `role`, `transcript_excerpt`) and `NarrativeRole` enum (INTRO, BUILDUP, CORE, REACTION, CONCLUSION) in the domain layer. But there is no container model to represent a complete narrative plan — the ordered collection of moments plus metadata about the plan itself. The transcript agent's JSON output also has no parser; downstream stages cannot deserialize a multi-moment structure.

This story adds the `NarrativePlan` domain model and an application-layer parser with graceful fallback: if the agent outputs malformed JSON or a single moment, the parser degrades to a single-moment `NarrativePlan` with a CORE role rather than crashing the pipeline.

## Story

As a pipeline developer,
I want a `NarrativePlan` domain model and a parser that extracts multi-moment structures from agent JSON output,
so that the pipeline can represent and deserialize narrative arcs with graceful fallback to single-moment on parse failure.

## Acceptance Criteria

1. Given the domain layer, when `NarrativePlan` is defined in `domain/models.py`, then it is a frozen dataclass with fields:
   - `moments: tuple[NarrativeMoment, ...]` (1-5 moments, ordered by narrative role)
   - `target_duration_seconds: float` (requested total duration)
   - `actual_duration_seconds: float` (sum of moment durations, computed property)
   - Validation: at least 1 moment, at most 5, exactly one CORE role present

2. Given a valid multi-moment JSON blob from `moment-selection.json` containing a `moments[]` array, when `parse_narrative_plan()` is called, then it returns a `NarrativePlan` with all moments deserialized and role-ordered

3. Given a single-moment JSON blob (legacy format with `start_seconds`/`end_seconds` at top level, no `moments[]` array), when `parse_narrative_plan()` is called, then it returns a `NarrativePlan` with one `NarrativeMoment` assigned role `CORE`

4. Given a malformed `moments[]` array (missing fields, invalid roles, overlapping timestamps), when `parse_narrative_plan()` encounters the error, then it logs a warning, falls back to single-moment extraction from the top-level `start_seconds`/`end_seconds`, and returns a valid `NarrativePlan`

5. Given a `NarrativePlan` with moments, when `actual_duration_seconds` is accessed, then it returns the sum of all moment durations (not including gaps between non-contiguous moments)

6. Given a `NarrativePlan`, when moments are checked for chronological source order, then a `is_chronological` property returns True if all moments are ordered by `start_seconds` (needed for I/O optimization in Story 16-4)

## Tasks

- [ ] Task 1: Add `NarrativePlan` frozen dataclass to `domain/models.py` with tuple field, validation, computed properties
- [ ] Task 2: Create `application/moment_parser.py` with `parse_narrative_plan()` function
- [ ] Task 3: Implement legacy single-moment fallback path in parser
- [ ] Task 4: Implement malformed-JSON fallback path with warning logging
- [ ] Task 5: Unit tests for NarrativePlan validation (min/max moments, exactly-one-CORE)
- [ ] Task 6: Unit tests for parser — multi-moment, single-moment legacy, malformed fallback

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/models.py` | Add `NarrativePlan` frozen dataclass after `NarrativeMoment` | Domain model |
| `src/pipeline/application/moment_parser.py` | New file — `parse_narrative_plan()` + fallback logic | Application layer |
| `tests/unit/domain/test_narrative_plan.py` | New file — NarrativePlan validation tests | Tests |
| `tests/unit/application/test_moment_parser.py` | New file — parser tests with all fallback paths | Tests |

## Technical Notes

- `NarrativePlan` follows existing domain conventions: frozen dataclass, `tuple` not `list`, `__post_init__` validation
- Parser lives in application layer (imports domain models, no third-party deps)
- The parser uses `TYPE_CHECKING` guard for port imports per project convention
- Fallback design is the key risk mitigation from consensus review — AI agents sometimes produce inconsistent JSON, so the parser must be resilient
- The `moments[]` JSON schema aligns with what Story 14-3 specified in the `moment-selection.json` extension

## Definition of Done

- `NarrativePlan` frozen dataclass in domain layer with full validation
- `parse_narrative_plan()` in application layer with 3 paths: multi-moment, legacy single, malformed fallback
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
