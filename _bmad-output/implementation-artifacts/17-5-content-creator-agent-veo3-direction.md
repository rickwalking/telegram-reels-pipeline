# Story 17-5: Content Creator Agent Veo3 Direction

## Context

The Content Creator agent (Stage 4) already generates `veo3_prompts[]` as part of `publishing-assets.json` (Epic 11). Currently, each prompt has only `variant` and `prompt` fields. This story updates the Content Creator's agent definition and QA gate to produce enriched prompts with narrative anchors, duration, and visual style direction — making the Content Creator the "editorial director" for B-roll placement.

The key design principle from the brainstorming session: the Content Creator specifies placement in story language (narrative anchors), not timestamps. It doesn't know the timeline yet — that's Assembly's job to resolve.

## Story

As a pipeline user,
I want the Content Creator agent to produce enriched `veo3_prompts` with narrative anchors, duration, and visual style direction,
so that the editorial director specifies clip placement and aesthetics in story language.

## Acceptance Criteria

1. Given the Content Creator agent prompt, when updated, then it instructs the agent to generate enriched veo3_prompts with all required fields

2. Given each veo3_prompt, when generated, then it includes:
   - `variant`: one of `intro`, `broll`, `outro`, `transition`
   - `prompt`: visual description including style direction matching the reel's aesthetic
   - `narrative_anchor`: story-language reference to a content moment (e.g., "distributed systems explanation", not "at 45 seconds")
   - `duration_s`: 5-8 seconds, director's choice per clip

3. Given variant types, when used as classification taxonomy, then they carry implicit placement semantics: `intro` → reel start, `outro` → reel end, `transition` → between narrative moments, `broll` → anchored to specific content moment

4. Given the visual style in prompts, when generated, then it matches the reel's overall aesthetic as determined by the Content Creator's analysis of the source material

5. Given clip count, when the Content Creator decides how many clips to generate, then the count is the director's choice based on narrative needs, capped by `VEO3_CLIP_COUNT`

6. Given the QA gate for Content Creator, when validating `publishing-assets.json`, then it checks:
   - Each veo3_prompt has all required fields (variant, prompt, narrative_anchor, duration_s)
   - `variant` is a valid taxonomy value
   - `duration_s` is within 5-8 range
   - `narrative_anchor` is non-empty and uses descriptive language (not timestamps)

7. Given `publishing-assets.json`, when schema is updated, then the enriched prompts are backward-compatible with the `Veo3Prompt` dataclass from Story 17-1

## Tasks

- [ ] Task 1: Update `agents/content-creator/agent.md` with enriched veo3_prompts instructions
- [ ] Task 2: Add B-roll style guidance to agent prompt (aesthetic coherence, narrative anchoring)
- [ ] Task 3: Update `qa/gate-criteria/content-criteria.md` with enriched prompt validation dimensions
- [ ] Task 4: Update sample `publishing-assets.json` schema documentation
- [ ] Task 5: Test QA gate catches missing fields, invalid variants, timestamp-based anchors

## Files Affected

| File | Change | Type |
|------|--------|------|
| `telegram-reels-pipeline/agents/content-creator/agent.md` | Update prompt to generate enriched veo3_prompts with narrative anchors + style | Agent definition |
| `telegram-reels-pipeline/qa/gate-criteria/content-criteria.md` | Add validation dimensions for enriched veo3_prompts | QA criteria |
| `tests/unit/test_content_creator_output.py` | New/updated — validate enriched prompt schema | Tests |

## Technical Notes

- The Content Creator doesn't know segment timestamps or the encoding plan — narrative anchors must be in story language ("when the host explains X") not timeline references ("at 1:23")
- The QA gate should flag timestamp-like patterns in narrative_anchor (e.g., regex for `\d+:\d+` or `\d+ seconds`) as a violation
- This story is independent of the adapter/orchestration stories and can be developed in parallel with Stories 17-3 and 17-4
- The enriched prompts flow: Content Creator generates → publishing-assets.json → Veo3Orchestrator reads (Story 17-4)

## Definition of Done

- Content Creator agent prompt generates enriched veo3_prompts with all fields
- QA gate validates enriched prompt structure and quality
- Narrative anchors use story language, not timestamps
- All tests pass, linters clean
