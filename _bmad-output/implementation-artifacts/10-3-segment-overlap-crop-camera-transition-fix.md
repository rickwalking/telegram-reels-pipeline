# Story 10.3: Segment Overlap Removal & Camera Transition Detection Fix

Status: in-progress

## Problem

Two quality regressions in the output video introduced during the face-position-intelligence refactoring (Story 10.2):

1. **Segment boundary repeats**: Audio and video repeat at every segment transition (~0.5-1s of duplicated content per boundary). Stage 6 adds 0.5s overlaps at transition points expecting Assembly to trim them, but the ReelAssembler uses FFmpeg concat with `-c copy` (stream copy) which cannot trim or crossfade.

2. **Crop cuts people off during camera transitions**: When the source video switches from a close-up (1 face) to a wide shot (2 faces) mid-segment, the narrow `speaker_focus` crop stays applied for the remainder, cutting off the second speaker. The 5s minimum hold rule prevents splitting at the camera transition, and the QA gate only checks that *at least one* face is in the crop — not that *all visible* faces are captured.

### Root Cause

1. **Overlap**: `crop-playbook.md` instructs "Add 0.5s overlap at transition points for smooth concatenation." `stage-06-ffmpeg-engineer.md` says "the Assembly stage trims the overlap." But `reel_assembler.py` uses `ffmpeg -f concat -c copy` which is a bitstream copy — no filtering, trimming, or blending is possible. The overlap instructions were added during 10.2 but the assembler was never updated to handle them.

2. **Camera transitions blocked by stability rules**: `crop-playbook.md` line 180 says "This applies everywhere — including at camera transitions." This means even when face count changes from 1 to 2 (clear camera switch), the agent cannot split the segment if the remaining duration would be <5s. The QA gate (Dimension 5: Face Validation) passes as long as *any* face is in the crop, missing the case where a visible person is cropped out.

3. **Stage 7 implies crossfade capability**: `stage-07-assembly.md` line 40 says "Use crossfade only if segments have overlapping content." The assembler cannot crossfade — this instruction is misleading and encourages the overlap behavior.

### Evidence

From run `20260212-205208-a5f7ac` (encoding-plan.json):
- Segment 1: ends at 1803.5s
- Segment 2: starts at 1802.5s (0.5s overlap with segment 1), ends at 1843.5s
- Segment 3: starts at 1842.5s (0.5s overlap with segment 2)
- Total encoded: 75s. Expected: 74s. Difference = exactly 2 x 0.5s untrimmed overlaps.

Segment 2 uses `speaker_focus` crop (720px) for 1802.5-1843.5s. Camera switches to wide shot at ~1840s showing both speakers, but the narrow crop persists, cutting off the right speaker for ~3s. Segment 3 correctly uses a both-visible crop (1150px) starting at 1842.5s.

## Story

As a pipeline user,
I want segment boundaries to be exact (no overlapping content) and camera angle transitions to be detected and handled (splitting the segment at the transition point),
so that the final video has clean cuts with no repeated audio and all visible speakers are properly framed at all times.

## Acceptance Criteria

1. Given segments produced by Stage 6, when segment boundaries are checked, then `next.start_seconds == prev.end_seconds` for all adjacent segments (no overlap, no gap)
2. Given a video where the camera switches from close-up to wide shot mid-segment, when the FFmpeg Engineer checks `face-position-map.json`, then it detects the face count change and splits the segment at the transition
3. Given a camera transition that would create a sub-segment shorter than 5s, when the FFmpeg Engineer applies stability rules, then the camera-transition exception allows the split regardless of duration
4. Given a segment where 2+ faces are visible and fit in one crop but only 1 is captured, when the QA gate evaluates, then it triggers Rework with a prescriptive fix template
5. Given a segment where speakers are too far apart to fit in one crop, when the QA gate evaluates the per-speaker sub-segments, then it does NOT false-fail (conditional rule)
6. Given the Assembly stage receives segments with exact boundaries, when it concatenates them, then the output has no repeated audio or video at transitions
7. Given Stage 7 workflow documentation, when the Assembly agent reads it, then it uses "cut" transitions only (no crossfade references)

## Tasks

- [ ] Task 1: Remove 0.5s overlap instruction from `crop-playbook.md`
- [ ] Task 2: Remove overlap instruction from `stage-06-ffmpeg-engineer.md`
- [ ] Task 3: Remove crossfade reference from `stage-07-assembly.md`
- [ ] Task 4: Add camera-transition exception to stability rules in `crop-playbook.md`
- [ ] Task 5: Strengthen camera-change detection in `crop-playbook.md`
- [ ] Task 6: Add face coverage validation to `ffmpeg-criteria.md` (conditional on speaker fit)
- [ ] Task 7: Create `crop-failure-modes.md` knowledge file (FM-1 through FM-3, no run IDs)
- [ ] Task 8: Update `crop-playbook.md` to reference knowledge file instead of inline examples
- [ ] Task 9: Update `agent.md` Knowledge Files section

## Files Affected

| File | Change | Type |
|------|--------|------|
| `agents/ffmpeg-engineer/crop-playbook.md` | Remove overlap, camera-transition exception, strengthen detection, reference knowledge file | Agent knowledge |
| `agents/ffmpeg-engineer/crop-failure-modes.md` | **New** — self-contained failure patterns | Agent knowledge |
| `agents/ffmpeg-engineer/agent.md` | Add knowledge file reference | Agent definition |
| `workflows/stages/stage-06-ffmpeg-engineer.md` | Exact boundaries, no overlap | Stage workflow |
| `workflows/stages/stage-07-assembly.md` | Remove crossfade, clarify `-c copy` | Stage workflow |
| `workflows/qa/gate-criteria/ffmpeg-criteria.md` | Conditional people-cut-off check | QA criteria |

## Technical Notes

- **No Python changes**: All fixes are in agent/workflow/QA markdown files. `reel_assembler.py` works correctly with clean boundaries.
- **Audio pops not a risk**: Each segment is independently re-encoded by Stage 6 with proper audio framing at exact timestamps. Concat of properly-framed segments produces clean joins.
- **5s detection floor**: Frame extraction happens every 5s in Stage 5. Camera transitions between extracted frames may not be detected. This is acceptable — stability rules enforce similar granularity. Scene change detection (FFmpeg `select='gt(scene,0.3)'`) could be a future enhancement to Stage 5.
- **Backward compatible**: Removing the overlap instruction doesn't break anything. The assembler always did `-c copy` concat. Previous runs without overlaps had clean output.
