---
stepsCompleted: [1, 2, 3, 4]
session_continued: true
continuation_date: 2026-02-25
inputDocuments: []
session_topic: 'Veo3 Animated B-Roll Integration into Reels Pipeline'
session_goals: 'Architectural fit for async Veo3 parallel step, assembly cut decisions, data flow from content prompts to Veo3 to assembly, fallback behavior'
selected_approach: 'ai-recommended'
techniques_used: ['Morphological Analysis', 'Role Playing', 'Decision Tree Mapping']
ideas_generated: [29]
context_file: ''
session_active: false
workflow_completed: true
epic_output: 'Epic 17 — 8 stories in _bmad-output/planning-artifacts/epics.md'
consensus_validated: true
---

# Brainstorming Session Results

**Facilitator:** Pedro
**Date:** 2026-02-23

## Session Overview

**Topic:** Integrating Gemini Veo3 async video generation as a parallel pipeline step (alongside Stages 5-6) that produces animated B-roll clips (silent) from prompts already generated during content creation, to be woven into the final assembly for richer visual narrative.

**Goals:**
- How to architecturally fit an async Veo3 generation step that runs parallel to Stages 5-6
- How Assembly (Stage 7) decides when to cut to a generated clip vs. stay on talking heads
- What the data flow looks like — from existing content prompts through Veo3 to assembly inputs
- Fallback behavior when Veo3 generation fails or times out (assembly proceeds without B-roll)

### Context Guidance

_Working within an established Telegram Reels Pipeline with hexagonal architecture, 7-stage pipeline (Router > Research > Transcript > Content > Layout Detective > FFmpeg Engineer > Assembly), frozen dataclasses in domain, port/adapter patterns, and async I/O conventions. Veo3 generation runs in the cloud — Pi hardware constraints are not a concern for this feature._

### Session Setup

_Pedro confirmed the session parameters. The Veo3 step runs parallel to Stages 5-6. No Pi hardware concerns since generation is cloud-based. Assembly stage needs to intelligently interleave generated B-roll with source video segments._

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Veo3 B-Roll Integration — hybrid problem requiring both technical architecture and creative editorial decisions

**Recommended Techniques:**

- **Morphological Analysis (Deep):** Systematically map all parameter dimensions — trigger timing, clip type, insertion point, fallback strategy — and explore promising combinations. Foundation for all downstream decisions.
- **Role Playing (Collaborative):** Stress-test the integration from four perspectives — Assembly Agent, Content Creator Agent, Viewer, Pipeline Orchestrator — to surface insights a purely technical analysis would miss.
- **Decision Tree Mapping (Structured):** Convert brainstorm insights into concrete assembly decision logic — the "if X then cut to B-roll" tree that drives implementation.

**AI Rationale:** Sequence moves from divergent exploration (morphological) through perspective testing (role play) to convergent action (decision tree). Covers both the engineering architecture and the editorial "feel" of when B-roll enhances vs. distracts.

## Technique Execution Results

### Morphological Analysis (Deep)

**Interactive Focus:** Mapped 8 architectural dimensions — trigger source, generation timing, clip format, editorial authority, placement model, parallel execution, assembly behavior, and fallback strategy.

**Key Ideas (11):**

1. **Trigger #1**: Veo3 prompts from `publishing-assets.json` — data source already exists, broll variant is required
2. **Timing #2**: Fire-and-forget during Stages 5-6 — exploits natural pipeline gap as free generation time
3. **Format #3**: Native 9:16 vertical generation — no post-processing rotation/cropping
4. **Assembly #4**: Conversation-driven insertion — Assembly uses content narrative to decide clip placement
5. **Fallback #5**: Bounded wait with graceful degradation (superseded by #6)
6. **Fallback #6**: Await-first with emergency fallback — clips are first-class, wait is the feature
7. **Fallback #7**: Per-clip status tracking — partial success beats all-or-nothing
8. **Architecture #8**: Content Creator as editorial director — single source of editorial truth
9. **Architecture #9**: Parallel generation with idempotent keys — `{run_id}_{variant}` pattern
10. **Schema #10**: Extended Veo3Prompt with placement + idempotent_key + duration fields
11. **Schema #11**: Deterministic idempotent keys from run context — zero collision risk

### Role Playing (Collaborative)

**Building on Previous:** Stress-tested morphological decisions from 4 stakeholder perspectives.

**Perspectives & Key Ideas (11):**

**Content Creator Agent (Director):**
12. **Role Play #12**: Narrative-anchored placement — story language, not timestamps. Director doesn't know the timeline yet.
13. **Role Play #13**: Variant as classification taxonomy — intro/broll/outro/transition are semantic labels, not positional instructions.

**Assembly Agent (Editor):**
14. **Assembly #14**: Timeline matching via narrative anchor — cross-reference against content.json and transcript
15. **Assembly #15**: Director-specified duration (5-8s) — editorial decision, not technical
16. **Assembly #16**: Documentary cutaway — silent video over continuous speaker audio
17. **Config #17**: Configurable `VEO3_CLIP_COUNT` — director decides count, config caps for cost control
18. **Assembly #18**: Reuse existing xfade transitions — 0.5s style-change for B-roll cuts

**Pipeline Orchestrator (Systems Engineer):**
19. **Infrastructure #19**: `veo3/jobs.json` for per-job state tracking with atomic writes
20. **Infrastructure #20**: Downloaded clips in run folder (superseded by #21)
21. **Infrastructure #21**: Dedicated `veo3/` subfolder in run directory

**Viewer (Audience):**
22. **Creative #22**: Director-specified visual style in prompts for aesthetic coherence

### Decision Tree Mapping (Structured)

**Building on Previous:** Crystallized all brainstorm insights into 3 concrete decision trees.

**Key Ideas (7):**
23. **Decision #23**: `VEO3_CLIP_COUNT` as maximum cap — creative freedom with financial safety net
24. **Decision #24**: Configurable `VEO3_TIMEOUT_S` — adapt after real API testing
25. **Decision #25**: Adaptive polling based on job status change — fast when active, patient when idle
26. **Production #26**: Veo3 watermark removal post-processing (superseded by #29)
27. **Production #27**: Tier-based watermark strategy — paid API removes visible watermark (research finding)
28. **Config #28**: Watermark handling as environment config (superseded by #29)
29. **Production #29**: Always-crop strategy — unconditional bottom strip crop, no config branching

### Decision Trees Produced

**Tree 1 — Generation Flow:**
Stage 4 completes → check publishing-assets.json → check veo3_prompts[] → cap at VEO3_CLIP_COUNT → generate idempotent keys → fire parallel async calls → start Stages 5-6 + polling worker

**Tree 2 — Await Gate:**
Stage 6 completes → check veo3/ folder → read jobs.json → all resolved? → evaluate (all completed / some failed / all failed) → download + crop → Stage 7. If not resolved: poll with exponential backoff until timeout.

**Tree 3 — Assembly Insertion:**
Read encoding-plan + content.json + veo3/ clips → for each clip: intro→start, outro→end, transition→between moments, broll→narrative anchor match → split segment, insert clip, documentary cutaway audio, xfade transitions → final-reel.mp4

## Idea Organization and Prioritization

### Thematic Organization

**Theme 1: Data Architecture & Schema** (#1, #10, #11, #12, #13, #17)
The Content Creator's existing `publishing-assets.json` output is the foundation. Extend the `Veo3Prompt` dataclass with narrative_anchor, duration_s, and idempotent_key. Variant types serve as classification taxonomy.

**Theme 2: Pipeline Flow & Infrastructure** (#2, #9, #19, #21, #24, #25)
Async generation fits the existing pipeline model. New primitives needed: polling worker with adaptive backoff, `veo3/` subfolder with `jobs.json` state tracking, configurable timeout.

**Theme 3: Await & Resilience** (#6, #7, #23)
Wait-first strategy — clips are essential to the final short. Per-clip independent tracking enables partial success. Director decides count, config caps it.

**Theme 4: Assembly & Editorial Intelligence** (#3, #4, #8, #14, #15, #16, #18)
Content Creator directs, Assembly executes. Narrative anchor matching drives insertion. Documentary cutaway model for audio continuity. Existing xfade transitions reused.

**Theme 5: Production Quality** (#22, #29)
Visual style specified in prompts for coherence. Unconditional bottom-strip crop for watermark removal.

### Prioritization Results

**Priority 1 — Must Build First (Foundation):**
- Extended Veo3Prompt schema (variant, prompt, narrative_anchor, duration_s, idempotent_key)
- Async generation service + polling worker (Gemini API integration)
- Await gate (new pipeline primitive before Stage 7)

**Priority 2 — Assembly Integration:**
- Assembly insertion logic (narrative anchor matching, documentary cutaway, xfade)
- Always-crop post-processing step

**Priority 3 — Configuration & Polish:**
- Environment config (VEO3_CLIP_COUNT, VEO3_TIMEOUT_S)
- Content Creator agent update (enriched veo3_prompts with placement + style direction)

### Architectural Decisions Summary

| Aspect | Decision |
|--------|----------|
| Data source | `veo3_prompts[]` in `publishing-assets.json` |
| Editorial authority | Content Creator is the director |
| Placement model | Narrative anchors, not timestamps |
| Variant taxonomy | intro/broll/outro/transition as classification |
| Generation | Parallel async calls with idempotent keys |
| Format | 9:16 vertical, silent |
| Clip duration | 5-8s, director-specified |
| Await strategy | Wait for all clips, proceed with whatever succeeds |
| Timeout | Configurable `VEO3_TIMEOUT_S` env var |
| Watermark | Always crop bottom strip |
| Clip storage | `veo3/` subfolder in run directory |
| Job tracking | `veo3/jobs.json` with per-clip status |
| Assembly insertion | Variant-driven placement logic |
| Audio model | Documentary cutaway — silent video over continuous speaker audio |
| Transitions | Reuse existing xfade system |
| Clip count | Configurable max, director decides actual count |
| Fallback | Emergency only — full failure or hard timeout |

## Session Summary and Insights

**Key Achievements:**
- 29 ideas across 8 architectural dimensions, 4 stakeholder perspectives, and 3 decision trees
- Complete architectural skeleton ready for epic/story breakdown
- Content Creator as editorial director emerged as the unifying design principle
- Gemini CLI research confirmed watermark strategy (always-crop)

**Creative Breakthroughs:**
- The data already exists — zero new AI prompt engineering work needed
- Narrative anchors decouple editorial intent from timeline mechanics
- Variant types double as both classification and placement hints
- The Stages 5-6 gap provides free generation time

**Session Reflections:**
Pedro brought sharp architectural instincts — particularly the idempotent key pattern, the "Content Creator as director" model, and the pragmatic always-crop watermark decision. The session moved efficiently from divergent exploration to convergent, implementable decisions.
