# Story 15.2: QA Gate — Boundary Frame Alignment Detection

## Context

Story 15-1 adds a prevention layer to the FFmpeg Engineer (Boundary Frame Guard). This story adds the detection layer: QA gate criteria that catch surviving boundary misalignment, ensuring wrong-crop artifacts are identified even if the prevention layer fails or the agent misinterprets the instructions.

This follows the Generator-Critic pattern used throughout the pipeline — the FFmpeg Engineer (generator) tries to prevent issues, the QA gate (critic) catches what remains.

## Story

As a pipeline user,
I want the QA gates to detect wrong-crop-at-boundary artifacts and issue prescriptive fixes,
so that misaligned boundaries are caught even when the FFmpeg Engineer's prevention layer misses them.

## Acceptance Criteria

1. Given `encoding-plan.json` with `boundary_validation` on every segment, when the FFmpeg QA gate evaluates Dimension 8 (Boundary Frame Alignment), then it passes if all face counts match expected or all mismatches have corresponding trims recorded
2. Given a segment with a face count mismatch at a boundary and no trim applied, when Dimension 8 evaluates, then it returns REWORK with a prescriptive fix template: "Segment {n} has {actual} face(s) at its {start|end} boundary but layout '{layout}' expects {expected}. Trim {start|end}_seconds by 1.0s"
3. Given `boundary_validation` is missing from any segment, when Dimension 8 evaluates, then it returns REWORK instructing the agent to run the Boundary Frame Guard check
4. Given segments with boundary trims that create duration gaps, when the Assembly QA Dimension 3 (Duration Accuracy) evaluates, then it recalculates expected duration by subtracting trimmed seconds — intentional gaps do not count as duration mismatches
5. Given cumulative boundary trims across all segments exceed 5.0 seconds per reel, when the Assembly QA Dimension 3 evaluates, then it flags as Fail regardless of intentional trim exemption (excessive content loss)
6. Given a multi-segment reel where the last frame of segment N and first frame of segment N+1 show an abrupt framing style change with no transition effect, when the Assembly QA Dimension 5 (Transition Quality) evaluates, then it flags the framing mismatch for rework with prescriptive fix
7. Given the FFmpeg QA weight redistribution, when all 8 dimension weights are summed, then the total equals exactly 100 (13+13+9+9+18+13+15+10)
8. Given `stage-07-assembly.md` instructions, when the Assembly agent reads them, then it references `boundary_validation` from `encoding-plan.json` for trim-aware duration calculation and logs trimmed gaps in `assembly-report.json`

## Tasks

- [ ] Task 1: Redistribute FFmpeg QA dimension weights in `workflows/qa/gate-criteria/ffmpeg-criteria.md` — reduce dims 1-6 to make room for 10-weight Dimension 8
- [ ] Task 2: Append Dimension 8 (Boundary Frame Alignment) to `workflows/qa/gate-criteria/ffmpeg-criteria.md` — pass/rework/fail criteria with prescriptive fix templates; add `boundary_validation` to Output Schema Requirements
- [ ] Task 3: Add boundary trim exemption + 5.0s cumulative cap to Dimension 3 (Duration Accuracy) in `workflows/qa/gate-criteria/assembly-criteria.md`
- [ ] Task 4: Add framing mismatch check to Dimension 5 (Transition Quality) in `workflows/qa/gate-criteria/assembly-criteria.md` — including weight upgrade to 10/100 for multi-segment reels
- [ ] Task 5: Update `workflows/stages/stage-07-assembly.md` — add trim-aware duration note referencing `boundary_validation`, log trimmed gaps in `assembly-report.json`

## Files Affected

| File | Change | Type |
|------|--------|------|
| `workflows/qa/gate-criteria/ffmpeg-criteria.md` | Redistribute weights, add Dimension 8 (10/100), add `boundary_validation` to schema | QA criteria |
| `workflows/qa/gate-criteria/assembly-criteria.md` | Add boundary trim exemption + 5s cap to Dim 3, framing mismatch to Dim 5 | QA criteria |
| `workflows/stages/stage-07-assembly.md` | Add trim-aware duration note, reference `boundary_validation` | Stage workflow |

## Technical Notes

- **Weight redistribution math**: Current 7 dims total 100. New 8 dims: 13+13+9+9+18+13+15+10 = 100. Dim 7 (Duration) unchanged at 15 because it's already the most relevant to boundary trim impacts.
- **Assembly Dim 5 weight**: Currently 0/100 (redistributed when no xfade transitions). For multi-segment reels, becomes 10/100 redistributed from Dims 1-4 (each loses 2.5).
- **Prescriptive fix templates**: Follow existing pattern from Dims 1-7 — include exact values and specific corrective instructions so the agent can fix without re-analyzing.
- **Cumulative trim cap**: 5.0s max total trims per reel prevents excessive content loss (5.0s on a 90s reel = 5.6%, still within normal editing tolerances).
- **Stage 7 update**: Assembly agent needs to read `boundary_validation` to correctly calculate expected duration and log trim gaps in the assembly report.
