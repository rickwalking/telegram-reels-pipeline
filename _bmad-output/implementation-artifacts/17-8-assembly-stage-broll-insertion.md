# Story 17-8: Assembly Stage B-Roll Insertion

## Context

After the await gate (Story 17-7) completes, the `veo3/` folder contains cropped and validated B-roll clips. Assembly (Stage 7) must now weave these clips into the final reel. The brainstorming session established the "documentary cutaway" model: silent Veo3 video plays OVER the continuous speaker audio — the audience hears the speaker while seeing the animated B-roll.

Codereview identified that the existing `_build_xfade_filter()` in `reel_assembler.py` couples video and audio streams, making it incompatible with the cutaway model. This story adds a new `_build_cutaway_filter()` method for independent video/audio stream mapping, leaving the existing xfade chain untouched.

Placement is variant-driven: `intro` → start, `outro` → end, `transition` → between moments, `broll` → matched to content via narrative anchors using semantic/fuzzy matching (not exact string match).

## Story

As a pipeline user,
I want the Assembly stage to weave Veo3 B-roll clips into the final reel using variant-driven placement and documentary cutaway audio model,
so that the finished short includes animated visuals that enhance the narrative without disrupting speaker audio.

## Acceptance Criteria

1. Given the Assembly stage, when it starts, then it reads available clips from `veo3/` folder and narrative anchors from `content.json`

2. Given variant-driven placement, when clips are positioned, then:
   - `intro` variant → inserted at reel start
   - `outro` variant → inserted at reel end
   - `transition` variant → inserted between narrative moments
   - `broll` variant → inserted at narrative anchor match point

3. Given `broll` variant placement, when matching narrative anchors, then semantic/fuzzy matching is used against content.json and transcript (not exact string match)

4. Given an unmatched narrative anchor, when no match is found, then the clip is skipped gracefully (no crash, warning logged)

5. Given B-roll clips, when spliced into the reel, then they are added to the segment list BEFORE the FFmpeg filter graph is constructed

6. Given the documentary cutaway model, when a B-roll clip is inserted, then `_build_cutaway_filter()` in `reel_assembler.py` maps the Veo3 video stream over the base segment's audio stream (independent video/audio stream mapping)

7. Given the existing `_build_xfade_filter()`, when B-roll is present, then it remains unchanged — cutaway uses a separate filter path

8. Given director-specified duration (5-8s), when a clip is inserted, then the cutaway duration matches the clip's actual duration

9. Given B-roll entry/exit points, when transitions are applied, then existing xfade system is reused: 0.5s style-change fade

10. Given no clips available (empty `veo3/` folder or all clips failed), when Assembly runs, then it proceeds normally without B-roll (graceful degradation)

11. Given the assembly report, when B-roll is used, then it includes: which clips were inserted, placement position, which clips were skipped and why

12. Given audio continuity, when a documentary cutaway plays, then the speaker's audio track continues uninterrupted — no silence, no audio crossfade during B-roll

## Tasks

- [ ] Task 1: Add B-roll clip discovery logic to Assembly stage (read `veo3/` folder + `content.json`)
- [ ] Task 2: Implement variant-driven placement resolver (intro/outro/transition/broll → position)
- [ ] Task 3: Implement semantic/fuzzy narrative anchor matching for `broll` variant
- [ ] Task 4: Implement skip fallback for unmatched anchors (log warning, continue)
- [ ] Task 5: Implement segment list splicing — insert B-roll clips at resolved positions before filter graph
- [ ] Task 6: Create `_build_cutaway_filter()` in `reel_assembler.py` — FFmpeg overlay with independent video/audio stream selection
- [ ] Task 7: Wire cutaway filter into assembly pipeline alongside existing xfade
- [ ] Task 8: Add 0.5s style-change xfade transitions at B-roll entry/exit points
- [ ] Task 9: Implement graceful degradation (no clips → normal assembly)
- [ ] Task 10: Add B-roll details to assembly report JSON
- [ ] Task 11: Update `workflows/stages/stage-07-assembly.md` with B-roll step
- [ ] Task 12: Update `qa/gate-criteria/assembly-criteria.md` with B-roll validation dimension
- [ ] Task 13: Integration tests for each placement variant
- [ ] Task 14: Integration test for audio continuity during cutaway
- [ ] Task 15: Integration test for no-clip fallback
- [ ] Task 16: Integration test for partial clips (some skipped)

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | New `_build_cutaway_filter()` method + B-roll segment splicing logic | Infrastructure adapter |
| `telegram-reels-pipeline/workflows/stages/stage-07-assembly.md` | Add B-roll discovery + insertion step | Workflow |
| `telegram-reels-pipeline/qa/gate-criteria/assembly-criteria.md` | Add B-roll validation dimension (audio continuity, placement accuracy) | QA criteria |
| `tests/integration/test_assembly_broll.py` | New file — placement variants, cutaway audio, graceful degradation | Tests |

## Technical Notes

- **`_build_cutaway_filter()` FFmpeg approach**: The key FFmpeg technique is `overlay` with time-bounded enable + stream selection. Example filter graph for inserting B-roll at timestamp T for duration D:
  ```
  [0:v]split[base][tmp];
  [tmp]trim=start=T:end=T+D,setpts=PTS-STARTPTS[trimmed];
  [1:v]scale=1080:1920[broll];
  [trimmed][broll]overlay=enable='between(t,0,D)'[cutaway];
  [base][cutaway]overlay=enable='between(t,T,T+D)'[v]
  ```
  Audio stays as `[0:a]` throughout — no crossfade on audio during cutaway
- **Semantic matching**: For narrative anchors, use simple keyword overlap or TF-IDF cosine similarity against transcript segments. Exact algorithm is implementation choice — the key requirement is it's not exact string match
- **Segment list ordering**: B-roll clips must be resolved to insertion points (timestamps) and spliced into the ordered segment list BEFORE the filter graph is built. The filter graph then treats them as part of the segment sequence
- This is the highest-complexity story in Epic 17. The FFmpeg filter graph for cutaways requires R&D — consider a spike or prototype before full implementation
- The existing `ReelAssembler.assemble()` method should detect whether B-roll clips are present and branch to the cutaway path vs. the existing xfade-only path

## Definition of Done

- Variant-driven placement resolves all four variant types
- `_build_cutaway_filter()` produces correct FFmpeg filter graph for documentary cutaway
- Speaker audio continues uninterrupted during B-roll
- Semantic narrative anchor matching with skip fallback
- Graceful degradation when no clips available
- Assembly report includes B-roll details
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
