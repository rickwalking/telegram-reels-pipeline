# Story 15.1: FFmpeg Engineer — Boundary Frame Guard Prevention

## Context

During pipeline run 20260221-163739-a56ac5 (ELIZA video), we discovered that camera transitions produce ~0.3–1s of misaligned framing. The split-screen filter was applied to frames where the camera had already switched to single-person (and vice versa). Root cause: `layout-analysis.json` boundary timestamps have ±1s resolution (5s grid with 1s fine-pass), but the actual camera switch happens between extracted frames. The FFmpeg agent blindly trusts these boundaries without verifying face count.

We manually fixed this by probing face count at 200ms intervals and trimming 1s from each boundary. This story codifies that fix as the prevention layer of a two-layer defense.

**Extends Story 10-3** (Segment Overlap & Camera Transition Fix) which established FM-1 through FM-3 and the camera transition detection rules. This story adds FM-4 and the pre-encode boundary verification protocol.

## Story

As a pipeline user,
I want the FFmpeg Engineer to verify face count at segment boundaries and trim misaligned boundaries before encoding,
so that camera transition frames are never encoded with the wrong crop filter.

## Acceptance Criteria

1. Given a segment where the camera transitions at its boundary (face count at last 1s ≠ expected for layout), when the FFmpeg Engineer reads `face-position-map.json`, then it detects the face count mismatch against the layout's expected count (`side_by_side` → 2+, `speaker_focus` → 1, `screen_share` → 0)
2. Given a face count mismatch at a segment boundary, when the agent applies the Boundary Frame Guard protocol, then the boundary is trimmed inward by 1.0 second and the trim is recorded in `boundary_validation` in `encoding-plan.json`
3. Given a 1.0s trim that would exceed 20% of the segment's total duration, when the guard evaluates, then the trim is skipped entirely (no partial trim)
4. Given a trim that would reduce a segment below 5 seconds, when the guard evaluates, then the trim is skipped (consistent with existing crop stability 5s minimum hold rule)
5. Given both boundaries of a segment need trimming but total trim would exceed 20% of duration, when the guard evaluates, then only the end boundary is trimmed (camera-out transitions are more visually jarring than camera-in)
6. Given no face data exists in `face-position-map.json` within the first/last 1s of a segment, when the guard evaluates, then `boundary_validation` records `no_data_at_boundary: true` and no trim is applied
7. Given adjacent segments where boundary trims created a gap of up to 2.0s, when the boundary integrity check (step 11) runs, then the gap is permitted when `boundary_validation` records the intentional trim
8. Given any segment in `encoding-plan.json`, when the agent outputs the plan, then every command includes a `boundary_validation` object (even if no trim was applied)
9. Given no face data at a segment boundary (`no_data_at_boundary: true`), when the agent selects a crop for that boundary region, then it biases toward the wider crop (a wide crop on a close-up is acceptable; a narrow crop on a wide shot cuts people off)

## Tasks

- [ ] Task 1: Add FM-4 to `agents/ffmpeg-engineer/crop-failure-modes.md` — wrong crop at camera transition boundary
- [ ] Task 2: Add "Boundary Frame Guard" section to `agents/ffmpeg-engineer/crop-playbook.md` — pre-encode verification protocol, gap tolerance, cumulative cap, edge cases (including no-data wider crop bias)
- [ ] Task 3: Add `boundary_validation` field to output contract in `agents/ffmpeg-engineer/agent.md` — field definition table + normative JSON schema + JSON example
- [ ] Task 4: Insert step 7 (Boundary Frame Guard) in `workflows/stages/stage-06-ffmpeg-engineer.md` — renumber steps 7-14 → 8-15, 15-18 → 16-19
- [ ] Task 5: Amend step 10→11 (boundary integrity) in `workflows/stages/stage-06-ffmpeg-engineer.md` — add contiguity exception for boundary trims

## Files Affected

| File | Change | Type |
|------|--------|------|
| `agents/ffmpeg-engineer/crop-failure-modes.md` | Append FM-4 after FM-3 | Agent knowledge |
| `agents/ffmpeg-engineer/crop-playbook.md` | Insert "Boundary Frame Guard" section after "Transition Handling" | Agent knowledge |
| `agents/ffmpeg-engineer/agent.md` | Add `boundary_validation` to Field Definitions table and JSON example | Agent definition |
| `workflows/stages/stage-06-ffmpeg-engineer.md` | Insert step 7, amend step 11, renumber all subsequent steps | Stage workflow |

## Technical Notes

- **No Python changes**: All fixes are in agent/workflow markdown files. The FFmpegAdapter and CliBackend work correctly — only the agent's instructions need updating.
- **Builds on existing data**: `face-position-map.json` already contains per-frame face counts at 1s intervals from Stage 5. No additional face detection runs needed.
- **5s minimum matches existing rule**: The crop stability rules in `crop-playbook.md` already mandate 5s minimum hold time. The Boundary Frame Guard respects this — never reduces a segment below 5s.
- **Step 7 placement rationale**: Placed after crop filter construction (step 6) but before quality degradation handling (step 8). This allows boundary adjustments to inform subsequent quality checks and encoding parameters.
