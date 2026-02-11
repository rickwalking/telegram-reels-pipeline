# Story 8.3: Revision Flow Definitions

Status: ready-for-dev

## Story

As a pipeline developer,
I want revision flow definition files written,
So that the RevisionRouter and RevisionHandler can execute targeted re-processing for each revision type without re-running the full pipeline.

## Acceptance Criteria

1. **Given** `workflows/revision-flows/` contains 4 revision flow files,
   **When** RevisionHandler processes a revision request,
   **Then** it loads the appropriate flow file to determine which stages to re-execute.

2. **Given** `revision-extend-moment.md` exists,
   **When** the user requests "make it longer" (EXTEND_MOMENT),
   **Then** the flow specifies: re-run FFMPEG_ENGINEER → ASSEMBLY → DELIVERY (matching `_REVISION_STAGES` in code).

3. **Given** `revision-fix-framing.md` exists,
   **When** the user requests "show the other speaker" (FIX_FRAMING),
   **Then** the flow specifies: re-run FFMPEG_ENGINEER → ASSEMBLY → DELIVERY (matching `_REVISION_STAGES` in code).

4. **Given** `revision-different-moment.md` exists,
   **When** the user requests "pick a different part" (DIFFERENT_MOMENT),
   **Then** the flow specifies: re-run TRANSCRIPT (exclude previous selection) → all downstream stages.

5. **Given** `revision-add-context.md` exists,
   **When** the user requests "add more context" (ADD_CONTEXT),
   **Then** the flow specifies: re-run FFMPEG_ENGINEER → ASSEMBLY → DELIVERY (matching `_REVISION_STAGES` in code).

6. **Given** a revision flow is executed,
   **When** the revised output is delivered,
   **Then** only the changed artifacts are re-delivered (incremental re-delivery per FR34).

## Tasks / Subtasks

- [ ] Task 1: Write `revision-extend-moment.md` (AC: #2)
  - [ ] Trigger: RevisionType.EXTEND_MOMENT
  - [ ] Re-execute stages (per code `_REVISION_STAGES`): FFMPEG_ENGINEER, ASSEMBLY, DELIVERY
  - [ ] Handler behavior (from `_extend_moment()`): adjusts start_seconds -15s and end_seconds +15s in moment-selection.json
  - [ ] Document: constraint that final duration should still be within 30-120s
  - [ ] Context passed: original moment selection, user's extension request

- [ ] Task 2: Write `revision-fix-framing.md` (AC: #3)
  - [ ] Trigger: RevisionType.FIX_FRAMING
  - [ ] Re-execute stages (per code): FFMPEG_ENGINEER, ASSEMBLY, DELIVERY
  - [ ] Handler behavior (from `_fix_framing()`): marks target segment with `needs_reframe=True` and user_instruction in layout-segments.json
  - [ ] Context passed: user's framing preference, original layout analysis

- [ ] Task 3: Write `revision-different-moment.md` (AC: #4)
  - [ ] Trigger: RevisionType.DIFFERENT_MOMENT
  - [ ] Re-execute stages (per code): TRANSCRIPT, CONTENT, LAYOUT_DETECTIVE, FFMPEG_ENGINEER, ASSEMBLY, DELIVERY
  - [ ] Handler behavior (from `_different_moment()`): writes revision-hint.json with type + timestamp_hint
  - [ ] Context passed: excluded moment timestamps, user's preference

- [ ] Task 4: Write `revision-add-context.md` (AC: #5)
  - [ ] Trigger: RevisionType.ADD_CONTEXT
  - [ ] Re-execute stages (per code): FFMPEG_ENGINEER, ASSEMBLY, DELIVERY
  - [ ] Handler behavior (from `_add_context()`): widens start -30s and end +30s, sets context_added=True in moment-selection.json
  - [ ] Context passed: original moment, user's context request

## Dev Notes

### CRITICAL: RevisionHandler is Hardcoded — Flow Files are Documentation-Only for MVP

`RevisionHandler` in `application/revision_handler.py` has `_REVISION_STAGES` hardcoded at line 17:
```python
_REVISION_STAGES: dict[RevisionType, tuple[PipelineStage, ...]] = {
    RevisionType.EXTEND_MOMENT: (FFMPEG_ENGINEER, ASSEMBLY, DELIVERY),
    RevisionType.FIX_FRAMING: (FFMPEG_ENGINEER, ASSEMBLY, DELIVERY),
    RevisionType.DIFFERENT_MOMENT: (TRANSCRIPT, CONTENT, LAYOUT_DETECTIVE, FFMPEG_ENGINEER, ASSEMBLY, DELIVERY),
    RevisionType.ADD_CONTEXT: (FFMPEG_ENGINEER, ASSEMBLY, DELIVERY),
}
```

The handler methods (`_extend_moment`, `_fix_framing`, etc.) are also hardcoded — they never read flow files from disk.

**Impact**: Writing revision flow `.md` files will NOT change runtime behavior.

**Scope for this story**: Write the flow files as **documentation/specification** that defines the intended behavior. The hardcoded `_REVISION_STAGES` already matches the intended flows. The flow files serve as:
1. Human-readable reference for the revision system design
2. Specification that can be validated against the code
3. Future migration path if flows need to be dynamic

**Note**: The story's AC about "stages to re-execute" should be validated against the hardcoded `_REVISION_STAGES` dict, NOT against file loading behavior.

**Discrepancy found**: Story 8.3 AC #2 says EXTEND_MOMENT re-runs TRANSCRIPT, but `_REVISION_STAGES` starts at FFMPEG_ENGINEER. The flow files should match the actual code behavior.

### Revision Flow Template

Each flow file should follow this structure:

```markdown
# Revision Flow: [Revision Type]

## Trigger
RevisionType.[ENUM_VALUE]

## Stages to Re-Execute
1. [Stage] — [modification description]
2. [Stage] — [modification description]
...

## Context Passed to Stages
- original_moment: [from previous run]
- user_request: [interpreted revision text]
- exclusions: [any data to skip]

## Incremental Re-Delivery
- Only re-deliver: [changed artifacts]
- Preserve from original: [unchanged artifacts]

## Constraints
- [Duration limits, quality minimums, etc.]
```

### Integration Points

- **RevisionRouter** (`application/revision_router.py`): classifies user feedback → RevisionType
- **RevisionHandler** (`application/revision_handler.py`): loads flow file, re-executes subset of stages
- **PipelineRunner**: can be called with `resume_from` stage to skip earlier stages
- **Incremental delivery**: DeliveryHandler re-sends only changed video/content

### PRD Functional Requirements

- FR29: Moment extension revision
- FR30: Framing fix revision
- FR31: Different moment revision
- FR32: Add context revision
- FR33: Interpret feedback and route to correct agent
- FR34: Incremental re-delivery of changed output

### File Locations

```
telegram-reels-pipeline/workflows/revision-flows/revision-extend-moment.md
telegram-reels-pipeline/workflows/revision-flows/revision-fix-framing.md
telegram-reels-pipeline/workflows/revision-flows/revision-different-moment.md
telegram-reels-pipeline/workflows/revision-flows/revision-add-context.md
```

### References

- [Source: prd.md#FR29-FR34] — Revision requirements
- [Source: retrospective-epics-1-6.md#Critical Gap 8] — Empty revision flows
- [Source: domain/enums.py#RevisionType] — EXTEND_MOMENT, FIX_FRAMING, DIFFERENT_MOMENT, ADD_CONTEXT
- [Source: application/revision_router.py] — RevisionRouter
- [Source: application/revision_handler.py] — RevisionHandler

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
