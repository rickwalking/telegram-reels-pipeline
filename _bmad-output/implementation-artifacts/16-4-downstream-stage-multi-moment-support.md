# Story 16-4: Downstream Stage Multi-Moment Support

## Context

Stories 16-1 through 16-3 produce a `NarrativePlan` with 2-5 moments. But stages 5-7 (Layout Detective, FFmpeg Engineer, Assembly) currently process a single time range. This story wires multi-moment support through the downstream stages, with a key optimization: **chronological I/O ordering** for Pi performance.

The Pi has limited I/O bandwidth and memory. Processing moments in source-video chronological order (by `start_seconds`) minimizes seeks on the source file and allows the Pi to process frames sequentially. The assembly stage then reorders segments into narrative role order for the final Reel.

**From Story 14-4**: The FFmpeg engineer already handles multi-segment encoding and the assembly stage supports xfade transitions with `TransitionKind.NARRATIVE_BOUNDARY`. This story extends those to iterate over `NarrativePlan.moments`.

## Story

As a pipeline user,
I want stages 5-7 to process multiple moments with chronological I/O ordering for Pi performance,
so that the full pipeline produces a coherent multi-moment Reel end-to-end.

## Acceptance Criteria

### Stage 5: Layout Detective

1. Given a `NarrativePlan` with N moments, when the layout detective executes, then it extracts frames for each moment's time range independently
2. Given multiple moments, when frames are extracted, then extraction happens in chronological source order (sorted by `start_seconds`) to minimize disk seeks
3. Given per-moment frame extraction, when face detection runs, then `face-position-map.json` includes a `moment_index` field grouping faces by their source moment
4. Given per-moment face data, when `layout-analysis.json` is produced, then it contains per-moment layout classifications (different moments may have different camera setups)

### Stage 6: FFmpeg Engineer

5. Given per-moment layout analysis, when the FFmpeg engineer encodes, then each moment is encoded as a separate segment group with its own crop strategy
6. Given multiple moments, when encoding runs on Pi, then moments are encoded in chronological source order (I/O optimization — sequential reads from source video)
7. Given per-moment encoding, when `encoding-plan.json` is produced, then each command includes `moment_index` and `narrative_role` fields
8. Given the boundary frame guard (Story 15-1), when it evaluates multi-moment segments, then it applies independently per moment (moment boundaries are NOT segment boundaries — they are separate extractions)

### Stage 7: Assembly

9. Given encoded moment segments, when assembly runs, then segments are reordered from chronological (I/O order) to narrative role order (intro → buildup → core → reaction → conclusion)
10. Given narrative role ordering, when transitions are applied between moments, then `TransitionKind.NARRATIVE_BOUNDARY` is used (1.0s dissolve) as established in Epic 14
11. Given transitions within a single moment's segments (style changes), when transitions are applied, then `TransitionKind.STYLE_CHANGE` is used (0.5s slide) — existing behavior preserved
12. Given `assembly-report.json`, when the report is produced, then it includes a narrative structure summary: moments used, role order, per-role screen time, total gaps between non-contiguous moments

### QA Criteria

13. Given the assembly QA gate, when evaluating multi-moment output, then new dimensions are checked:
    - **Narrative ordering**: Segments appear in correct narrative role order in the final Reel
    - **Transition consistency**: NARRATIVE_BOUNDARY transitions between moments, STYLE_CHANGE within moments
    - **Total duration**: Final Reel duration is within ±15% of `target_duration_seconds` (accounting for transition overlaps)

## Tasks

- [ ] Task 1: Update `workflows/stages/stage-05-layout-detective.md` — add multi-moment frame extraction loop, chronological ordering, per-moment face grouping
- [ ] Task 2: Update `workflows/stages/stage-06-ffmpeg-engineer.md` — add per-moment encoding loop, chronological I/O order, moment_index/narrative_role in encoding-plan
- [ ] Task 3: Update `workflows/stages/stage-07-assembly.md` — add chronological-to-narrative reorder step, transition type selection, narrative structure report
- [ ] Task 4: Update `qa/gate-criteria/assembly-criteria.md` — add narrative ordering, transition consistency, total duration dimensions
- [ ] Task 5: Update agent definitions for stages 5-7 with multi-moment awareness in persona instructions

## Files Affected

| File | Change | Type |
|------|--------|------|
| `workflows/stages/stage-05-layout-detective.md` | Add multi-moment loop, chronological ordering | Stage workflow |
| `workflows/stages/stage-06-ffmpeg-engineer.md` | Add per-moment encoding, I/O ordering, moment fields | Stage workflow |
| `workflows/stages/stage-07-assembly.md` | Add reorder step, transition selection, narrative report | Stage workflow |
| `qa/gate-criteria/assembly-criteria.md` | Add 3 new QA dimensions for multi-moment assembly | QA criteria |
| `agents/layout-detective/agent.md` | Add multi-moment awareness to persona | Agent definition |
| `agents/ffmpeg-engineer/agent.md` | Add multi-moment encoding instructions | Agent definition |
| `agents/assembly/agent.md` | Add narrative reorder instructions | Agent definition |

## Technical Notes

- **No Python changes**: All modifications are in agent/workflow/QA markdown files. The `NarrativePlan` model and parser from Story 16-1 handle the data layer. The `reel_assembler.py` adapter already supports `TransitionKind.NARRATIVE_BOUNDARY` from Epic 14.
- **Chronological I/O ordering is critical for Pi**: The Pi 5's SD card and USB storage have limited random-seek performance. Processing moments in source order means FFmpeg reads the video file sequentially. Assembly reorders afterward using the already-encoded segment files (small, fast seeks).
- **Moment boundaries vs. segment boundaries**: A moment may contain multiple segments (due to style changes within the moment). The boundary frame guard from Story 15-1 applies at segment boundaries within a moment, not at moment boundaries. Moment transitions use the 1.0s dissolve, not the boundary trim.
- **Backwards compatibility**: When `NarrativePlan` contains a single moment, all stages behave identically to the current pipeline. The loop body executes once, no narrative reordering is needed, and no NARRATIVE_BOUNDARY transitions are applied.

## Definition of Done

- Stages 5-7 process multi-moment NarrativePlans correctly
- Chronological I/O ordering verified in workflow steps
- Assembly reorders to narrative role order with correct transition types
- QA criteria enforce narrative structure in final output
- Single-moment behavior unchanged (backwards compatible)
