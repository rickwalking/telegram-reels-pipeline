# Story 16-3: Transcript Agent Multi-Moment Selection

## Context

The transcript agent (Stage 3) currently selects a single continuous 60-90s block from the transcript. When multi-moment mode is active (`moments_requested >= 2`), the agent must instead select 2-5 complementary moments that build a narrative arc across the episode.

This is primarily a prompt engineering change to the transcript agent's definition and workflow, plus QA criteria updates to validate narrative coherence. This story carries the highest risk in Epic 16 — AI agent quality for multi-moment selection depends heavily on prompt design and QA feedback loops.

**Risk mitigation** (from consensus review): QA criteria must enforce chronological source ordering, minimum per-moment duration, and narrative role uniqueness to prevent degenerate selections.

## Story

As a pipeline user,
I want the transcript agent to select 2-5 complementary moments with narrative roles when multi-moment mode is active,
so that extended shorts follow a coherent narrative arc instead of one long continuous block.

## Acceptance Criteria

1. Given `moments_requested >= 2` in the workspace context, when the transcript agent executes `stage-03-transcript.md`, then it selects `moments_requested` moments from the transcript with narrative roles assigned from `NarrativeRole` (INTRO, BUILDUP, CORE, REACTION, CONCLUSION)

2. Given a multi-moment selection, when the agent outputs `moment-selection.json`, then it contains a `moments[]` array where each entry has:
   - `start_seconds`, `end_seconds` (precise timestamps)
   - `role` (one of: intro, buildup, core, reaction, conclusion)
   - `transcript_excerpt` (relevant text)
   - `selection_rationale` (why this moment serves this narrative role)

3. Given a multi-moment selection, when roles are assigned, then:
   - Exactly one moment has role `core` (the main hook/insight)
   - No duplicate roles (each role appears at most once)
   - Roles follow narrative arc order: intro → buildup → core → reaction → conclusion
   - Not all roles are required — a 2-moment short might use only `intro` + `core`

4. Given a multi-moment selection, when moments are validated, then:
   - Each moment is at least 15 seconds long (minimum for meaningful content)
   - Total duration of all moments is within ±20% of `target_duration_seconds`
   - Moments do not overlap in source timestamps
   - Moments are from different parts of the transcript (minimum 30s gap between moments)

5. Given the QA gate for transcript stage, when evaluating multi-moment output, then new dimensions are checked:
   - **Narrative coherence**: Do the moments tell a coherent story when presented in role order?
   - **Moment diversity**: Are moments from sufficiently different parts of the episode?
   - **Role appropriateness**: Does each moment's content match its assigned role?
   - **Duration balance**: No single moment exceeds 60% of total duration

6. Given `moments_requested = 1` (single-moment mode), when the transcript agent runs, then behavior is identical to the current pipeline (backwards compatible)

## Tasks

- [ ] Task 1: Update `agents/transcript/agent.md` — add multi-moment persona instructions, narrative role definitions, selection strategy
- [ ] Task 2: Update `agents/transcript/moment-selection-criteria.md` — add multi-moment selection rubric, minimum gap/duration rules
- [ ] Task 3: Update `workflows/stages/stage-03-transcript.md` — add conditional multi-moment step, output schema with `moments[]`
- [ ] Task 4: Update `qa/gate-criteria/transcript-criteria.md` — add narrative coherence, diversity, role appropriateness, duration balance dimensions
- [ ] Task 5: Add example multi-moment `moment-selection.json` to agent knowledge as a reference template

## Files Affected

| File | Change | Type |
|------|--------|------|
| `agents/transcript/agent.md` | Add multi-moment persona + selection strategy | Agent definition |
| `agents/transcript/moment-selection-criteria.md` | Add multi-moment rubric + constraints | Agent knowledge |
| `workflows/stages/stage-03-transcript.md` | Add conditional multi-moment step + output schema | Stage workflow |
| `qa/gate-criteria/transcript-criteria.md` | Add 4 new QA dimensions for multi-moment | QA criteria |

## Technical Notes

- **No Python changes**: All fixes are in agent/workflow/QA markdown files. The parser from Story 16-1 handles deserialization.
- **Prompt engineering is the primary risk**: Multi-moment selection quality depends on clear instructions, good examples, and tight QA feedback. The Generator-Critic pattern (max 3 attempts) provides the safety net.
- **Minimum 30s gap rule**: Prevents the agent from selecting adjacent transcript blocks and calling them "separate moments" — the goal is narrative diversity across the episode.
- **Role subset is valid**: A 2-moment short (e.g., intro + core) is perfectly fine. Not every narrative role needs to be filled.
- **Backwards compatibility**: When `moments_requested = 1`, the agent uses the existing single-moment prompt path. The output JSON includes `moments[]` with one entry for consistency, plus top-level `start_seconds`/`end_seconds` for legacy consumers.

## Definition of Done

- Transcript agent handles both single-moment and multi-moment modes
- QA criteria enforce narrative coherence and moment constraints
- Output schema documented with `moments[]` array
- Existing single-moment behavior unchanged when `moments_requested = 1`
