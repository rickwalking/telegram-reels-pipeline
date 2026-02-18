---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: []
session_topic: 'User-selectable framing styles for Reels pipeline — PiP, horizontal split-screen, and dynamic layout modes using OpenCV face detection'
session_goals: 'Define available framing/layout modes, design user interaction for style selection via CLI/Telegram, explore creative layout possibilities, consider FFmpeg feasibility on Raspberry Pi'
selected_approach: 'ai-recommended'
techniques_used: ['Morphological Analysis', 'SCAMPER Method', 'Chaos Engineering']
ideas_generated: [65]
context_file: ''
technique_execution_complete: true
consensus_validated: true
session_active: false
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Pedro
**Date:** 2026-02-18

## Session Overview

**Topic:** User-selectable framing styles for the Reels pipeline — Picture-in-Picture (PiP), horizontal split-screen, and dynamic layout modes using existing OpenCV face detection intelligence

**Goals:**
- Define the available framing/layout styles and how they map to face detection data
- Design user interaction for style selection (CLI `--style` flag, Telegram message keywords)
- Explore creative layout possibilities that differentiate the tool
- Consider FFmpeg filter_complex feasibility and performance on Raspberry Pi ARM
- Determine how styles interact with existing crop playbook and camera transition handling

### Session Setup

_Session initialized for brainstorming new framing modes. The pipeline already detects face positions (Speaker_Left, Speaker_Right), camera transitions, and speaker timelines. The challenge is translating these data sources into multiple visual presentation styles that users can select._

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Framing styles for Reels pipeline with focus on layout modes, UX design, FFmpeg feasibility

**Recommended Techniques:**
- **Morphological Analysis:** Systematically map all parameter combinations (speaker count x camera angle x style x emphasis x transitions)
- **SCAMPER Method:** Innovate within each layout combination — substitute, combine, adapt, modify
- **Chaos Engineering:** Stress-test ideas against edge cases, Pi constraints, and failure scenarios

## Technique Execution Results

### Morphological Analysis — Layout Parameter Matrix

65 ideas generated across 6 clusters:

#### Split-Screen Family
- **#1 Horizontal Split-Screen** — Two 1080x960 halves, each speaker face-centered independently
- **#4 Active Speaker Highlight Split** — 60/40 height ratio favoring active speaker
- **#5 Side-by-Side Vertical** — Two 540x1920 vertical strips
- **#6 Interview Mode (Asymmetric)** — Guest 70%, host 30% thin strip
- **#8 Cinematic Letterbox Split** — Two 2.39:1 widescreen bars stacked with black divider
- **#21 Two-Pass Split** — Separate FFmpeg passes per speaker, then vstack
- **#22 Single-Pass Split** — FFmpeg split filter for single decode pass
- **#26 Three-Speaker Triangular** — Top speaker full-width, bottom two side-by-side

#### PiP Family
- **#2 PiP (Picture-in-Picture)** — Active speaker full-screen, inactive in small corner overlay
- **#3 Dynamic PiP** — Animated swap when active speaker changes
- **#7 Reaction Strip** — Full-screen speaker + thin 200px reaction bar at bottom
- **#12 Circle Crop PiP** — Inactive speaker in circular bubble overlay (WhatsApp aesthetic)
- **#23 PiP via Overlay Filter** — Lightweight FFmpeg overlay, Pi-friendly at 280x500

#### Dynamic Behavior
- **#9 Focus Pull** — Split expands to full-screen during monologues, splits back for dialogue
- **#10 Pulse Zoom** — Active speaker gets subtle zoom-in, inactive gets zoom-out
- **#11 Spotlight Dim** — Inactive speaker gets brightness reduction or slight blur
- **#19 Style Mixing Within a Reel** — Different styles per segment based on content
- **#24 Animated Transitions via Xfade** — Smooth fade/slide between style phases

#### Content-Enhanced
- **#13 Quote Card Overlay** — Semi-transparent text overlay with impactful transcript quotes
- **#14 Mirror Mode** — Mirror one speaker so they face each other in split
- **#28 Waveform Visualization** — Audio waveform bar showing speaking energy per speaker
- **#29 Speaker Name Labels** — Auto-generated lower-third graphics from research data
- **#30 B-Roll Cutaway** — Insert Veo3-generated b-roll during long monologues

#### User Interaction
- **#15 Style Presets via CLI Flag** — `--style split`, `--style pip`, `--style auto`
- **#16 Natural Language Style in Message** — "make a pip style reel" parsed by Router agent (USER PREFERRED)
- **#17 Style Gallery Preview** — Telegram photo gallery of 5-second previews per style (USER PREFERRED)
- **#18 Auto-Style Based on Content** — AI picks style from mood_category and content analysis (USER PREFERRED)
- **#20 Style + Mood Pairing** — Map styles to mood_category from content.json

#### Visual Polish
- **#25 Border and Divider Styling** — Colored dividers, rounded corners, brand accent colors
- **#27 Solo Speaker Cinematic** — Letterbox + vignette + ken-burns pan for single-speaker moments
- **#47 Thumbnail Frame Selection** — Auto-select best thumbnail from final reel frames

### SCAMPER — Creative Innovations

#### Scene Understanding (Camera-Aware AI Director)
- **#31 Screen Share Detection + Auto-Split** — Detect screen share, auto-switch to content-top/speaker-bottom
- **#32 Layout Transition Journal** — `style-transitions.json` logging every style change with frame evidence and reasoning
- **#33 Camera-Aware Style State Machine** — FSM with states: split_screen, pip, full_speaker, screen_share_split, cinematic_solo
- **#34 Hybrid Screen Share + Reaction** — Content 70% top, speaker reaction 30% bottom, fades when silent
- **#35 Multi-Signal Layout Scoring** — Score each candidate style per frame across face count, text density, motion, speaker activity
- **#36 User Style Preference as Weight** — `--style pip` adds weight to scoring, doesn't force override
- **#37 Frame Diff Detection** — OpenCV frame differencing for precise camera cut detection
- **#38 Screen Share Content OCR** — Tesseract OCR on detected screen shares for content context
- **#39 Presentation Mode** — Slides 80% + speaker circle 20% for webinar/conference content
- **#40 Whiteboard/Demo Detection** — Wider crop preserving speaker's hands and surroundings

#### Competitive Moat
- **#41 Podcast DNA Fingerprint** — Learn show visual patterns over multiple runs via `show-profile.json`
- **#42 Multi-Source Intelligence Stack** — VTT + face detection + frame diff + content analysis + speaker ID fusion
- **#43 Open Framing Protocol** — `framing-spec.json` schema for shareable style recipes
- **#44 Creator Style Marketplace** — Community repository of style presets
- **#45 Real-Time Decision Explanation** — Telegram summary of style decisions with review/override capability (USER PREFERRED)
- **#46 Platform-Aware Output** — Adjust style weights per target platform (Reels vs Shorts vs LinkedIn)

#### Implementation Strategy
- **#48 Phase 0 — Style Flag Passthrough** — `--style` CLI + Telegram keyword → elicitation context
- **#49 Phase 1 — Horizontal Split** — `filter_complex` with two crops + vstack
- **#50 Phase 2 — PiP** — Overlay filter with active speaker detection
- **#51 Phase 3 — Screen Share Detection** — OpenCV + face count heuristic
- **#52 Phase 4 — Style State Machine** — Domain model `FramingStyle`, transition rules, per-segment directives
- **#53 Phase 5 — Style Transitions Journal** — Explainability artifact with frame references
- **#54 Phase 6 — Auto-Style Intelligence** — Multi-signal scoring + user preference weights

### Chaos Engineering — Failure Modes & Mitigations

- **#55 Face Detection Fails Mid-Segment** — Hold last known positions for 10s, then fall back to full-frame crop
- **#56 Split-Screen Mismatched Faces** — Independent y-offset per half to normalize vertical position
- **#57 Screen Share No Visible Speaker** — Frozen PiP from last frame or voice-only full-screen content
- **#58 Three+ Speakers** — Detect face count >2, escalate to multi-speaker layout or fall back to wide crop
- **#59 Rapid Camera Switching** — Adaptive hysteresis: increase minimum hold time in high-frequency-cut videos
- **#60 PiP Covers Important Content** — Smart positioning analyzing frame content for least-important corner
- **#61 Audio Desync at Style Transition** — Snap transition timestamps to nearest AAC audio frame boundary
- **#62 Memory Explosion on Pi** — Profile each style's peak memory; auto-downgrade or chunk processing
- **#63 Unsupported Style Request** — Detect impossibility in Stage 5, communicate via Telegram with fallback suggestion
- **#64 Style Transition Mid-Word** — Delay transitions to nearest speaker pause/breath from audio amplitude
- **#65 Encoding Time Explosion** — Style complexity tiers (fast/premium), hardware-aware selection

## Consensus Validation (Multi-Model Review)

### Models Consulted
- **Gemini 2.5 Pro (Advocate):** 9/10 confidence
- **Gemini 2.5 Pro (Critic):** 3/10 confidence

### Points of Agreement
1. User value is exceptionally high — transforms crop tool into AI video director
2. Phases 0-2 are safe and deliverable
3. Memory and encoding time on Pi are the #1 existential risk
4. Graceful degradation and user communication are critical

### Points of Disagreement
- **Phases 4-6 feasibility:** Advocate says FSM fits architecture cleanly; Critic says it's brittle and over-engineered for Pi
- **Screen share detection:** Advocate approves OpenCV approach; Critic suggests simple "no faces for X seconds" heuristic first
- **Style Transitions Journal:** Advocate calls it trust-building; Critic calls it a red flag for over-complexity

### Revised Implementation Plan (Consensus-Adjusted)

**Phase 0** — Style flag passthrough (`--style` CLI + Telegram keywords)
**Phase 1** — Horizontal split + vertical face alignment + 1-speaker fallback
**Phase 2** — PiP + overlay + 1-speaker graceful handling
**BENCHMARK GATE** — Pi memory/time profiling for split and PiP filter chains
**Phase 3** — Screen share detection (simple heuristic first: face count = 0 for >3s)
**Phase 4a** — Static style per clip (user picks one, applied globally)
**Phase 4b** — Dynamic style switching (FSM) — only if benchmarks pass
**Phase 5** — Style transitions journal (debug/QA tool first, user-facing second)
**Phase 6** — Auto-style intelligence (multi-signal scoring + user preference weights)
**Phase 7** — Advanced features: animated transitions (xfade), audio waveform visualization, OCR on screen shares

### Priority Chaos Fixes (During Phases 1-2)
1. Memory profiling of filter_complex on Pi
2. Vertical face alignment (independent y-offset per split half)
3. 1-speaker fallback with user communication
4. 3+ speaker detection with graceful fallback to wide crop

### Key User-Preferred Ideas
- **#16** Natural language style in Telegram message
- **#17** Style gallery preview via Telegram
- **#18** Auto-style based on content analysis
- **#19** Style mixing within a single Reel (USER PREFERRED)
- **#24** Animated transitions via xfade (USER PREFERRED)
- **#45** Real-time decision explanation in Telegram

---

## Idea Organization and Implementation Stories

**Analyst:** Mary (Business Analyst Agent)
**Organization Date:** 2026-02-18

### Thematic Organization

65 ideas mapped across **2 epics, 10 stories**. Every idea is assigned to a story. 3 long-term vision ideas are deferred to a future backlog epic.

### Epic Structure

| Epic | Title | Phase Coverage | Stories |
|------|-------|---------------|---------|
| **Epic 12** | Framing Styles — Core Layout Modes | Phase 0-3 + Benchmark Gate | 5 stories |
| **Epic 13** | Framing Styles — Intelligence & Polish | Phase 4-7 | 5 stories |

---

### Epic 12: Framing Styles — Core Layout Modes

Delivers the foundational framing engine: style selection plumbing, the two primary layout modes (split-screen and PiP), Pi performance validation, and screen share detection. User can select styles via CLI or Telegram and get properly rendered multi-speaker layouts.

#### Story 12-1: Style Selection Passthrough

**Slug:** `12-1-style-selection-passthrough`
**Phase:** 0
**Mapped Ideas:** #15, #16, #20, #48, #63
**User-Preferred:** #16 (Natural language style in Telegram)

**Scope:** Introduce `--style <name>` CLI flag and Telegram keyword parsing ("make a pip style reel"). The Router agent extracts style from natural language and passes it through the elicitation context to downstream stages. Add `FramingStyle` as a domain value object. No visual changes yet — pure plumbing.

**Acceptance Criteria:**
1. `--style split|pip|auto` argument available in CLI (`run_cli.py`)
2. Router agent parses style keywords from Telegram messages and includes `framing_style` in `router-output.json`
3. `FramingStyle` domain model exists with values: `default`, `split_horizontal`, `pip`, `auto`
4. Style choice propagates through elicitation context to Stage 5 and 6
5. Invalid style request → Telegram message with supported options + fallback to `default`

---

#### Story 12-2: Horizontal Split-Screen

**Slug:** `12-2-horizontal-split-screen`
**Phase:** 1
**Mapped Ideas:** #1, #4, #5, #6, #8, #14, #21, #22, #26, #49, #56, #58

**Scope:** Implement the primary horizontal split-screen layout using `filter_complex` with two independent crops + `vstack`. Each speaker is face-centered in their half. Includes vertical face alignment (independent y-offset per half), 1-speaker fallback to cinematic solo, and 3+ speaker detection with graceful wide-crop fallback. Initial version is 50/50 split; variant ratios (60/40, 70/30) as stretch goals.

**Acceptance Criteria:**
1. `style=split_horizontal` produces 1080x1920 output with two 1080x960 halves, each speaker face-centered
2. Independent y-offset per split half normalizes vertical face positions
3. 1-speaker segments fall back to cinematic solo crop with log message
4. 3+ speaker segments fall back to wide crop with log message
5. FFmpeg uses single-pass `filter_complex` with `split` filter for one decode pass
6. `setsar=1` appended to the final filter chain

---

#### Story 12-3: Picture-in-Picture Overlay

**Slug:** `12-3-pip-overlay`
**Phase:** 2
**Mapped Ideas:** #2, #3, #7, #12, #23, #50, #55, #60

**Scope:** Implement PiP using FFmpeg's `overlay` filter. Active speaker fills the frame; inactive speaker appears in a small corner overlay (280x500, Pi-friendly). Includes smart PiP positioning (analyze frame content for least-important corner), circle crop option, reaction strip variant (full-screen + 200px bar), and 1-speaker fallback. Face detection failure holds last known positions for 10s then falls back to full-frame.

**Acceptance Criteria:**
1. `style=pip` produces 1080x1920 output with active speaker full-screen and inactive in corner overlay
2. PiP overlay is Pi-friendly: 280x500 using lightweight `overlay` filter
3. PiP position avoids covering the active speaker's face (smart corner selection)
4. Face detection failure → hold last known position for 10s, then fall back to full-frame crop
5. 1-speaker segments fall back to cinematic solo
6. `setsar=1` appended to final chain

---

#### Story 12-4: Pi Performance Benchmark Gate

**Slug:** `12-4-pi-performance-benchmark-gate`
**Phase:** Benchmark Gate
**Mapped Ideas:** #62, #65

**Scope:** Profile memory consumption, CPU usage, and encoding time for split-screen and PiP filter chains on Raspberry Pi 4. Establish style complexity tiers (fast/premium). Results determine go/no-go for Phases 4+. If benchmarks fail, auto-downgrade to simpler styles or chunk processing.

**Acceptance Criteria:**
1. Benchmark script measures peak RSS memory, CPU%, and wall-clock time for `default`, `split_horizontal`, and `pip` styles
2. Tests use standardized 90-second source clip at 1080p
3. Results documented with pass/fail thresholds (e.g., <1.5GB memory, <4x realtime encoding)
4. Style complexity tiers defined: `fast` (single filter chain) and `premium` (multi-filter complex)
5. Go/no-go recommendation for Phases 4+ based on measured headroom

---

#### Story 12-5: Screen Share Detection

**Slug:** `12-5-screen-share-detection`
**Phase:** 3
**Mapped Ideas:** #31, #34, #37, #39, #40, #51, #57, #59

**Scope:** Detect screen share segments using face count heuristic (0 faces for >3s). When detected, auto-switch to content-top/speaker-bottom horizontal split. Includes frame diff detection for precise camera cut timing, presentation mode (slides 80% + speaker circle 20%), whiteboard/demo detection (wider crop preserving hands). Rapid camera switching → adaptive hysteresis. Screen share with no visible speaker → frozen PiP from last frame.

**Acceptance Criteria:**
1. Segments with 0 faces for >3 consecutive frames are flagged as screen share in `layout-analysis.json`
2. Screen share segments auto-apply content-top (70%) / speaker-bottom (30%) split
3. When no speaker face is available during screen share, last known speaker frame is frozen as PiP
4. Frame diff detection identifies camera cuts between extracted frames (threshold-based)
5. Detection thresholds are configurable in agent knowledge files

---

### Epic 13: Framing Styles — Intelligence & Polish

Builds the intelligence layer on top of the core engine: dynamic per-segment style switching via FSM, explainability artifacts, AI-driven auto-style selection, animated transitions, and content-enhanced overlays.

**Gate:** Epic 13 only proceeds if Story 12-4 (benchmark gate) passes.

#### Story 13-1: Dynamic Style Switching (FSM)

**Slug:** `13-1-dynamic-style-switching-fsm`
**Phase:** 4a + 4b
**Mapped Ideas:** #9, #10, #11, #19, #33, #52, #61, #64

**Scope:** Implement `FramingStyle` state machine in the domain layer with states: `solo`, `duo_split`, `duo_pip`, `screen_share`, `cinematic_solo`. Phase 4a: static style per clip (user picks one, applied globally). Phase 4b: dynamic per-segment switching based on scene data. Includes focus pull (expand/collapse between split and solo), pulse zoom on active speaker, spotlight dim on inactive. Transition timestamps snap to nearest speaker pause to avoid mid-word cuts. Audio sync validated at style transition boundaries.

**Acceptance Criteria:**
1. `FramingStyle` FSM domain model with transition table (pure data, no I/O)
2. Static mode: user-selected style applies to all segments uniformly
3. Dynamic mode: FSM transitions between styles based on face count changes and speaker timeline
4. Style transitions snap to nearest audio pause/breath (amplitude-based)
5. `encoding-plan.json` includes per-segment `framing_style` directive
6. Audio desync at transitions prevented by snapping to AAC frame boundaries

---

#### Story 13-2: Style Transitions Journal & Decision Explanation

**Slug:** `13-2-style-transitions-journal`
**Phase:** 5
**Mapped Ideas:** #32, #45, #53
**User-Preferred:** #45 (Real-time decision explanation)

**Scope:** Generate `style-transitions.json` logging every style change with frame timestamp, chosen style, reason, and source signals. Human-readable explanation output for QA/debugging. Telegram summary of style decisions sent to user with key decision points and frame evidence.

**Acceptance Criteria:**
1. `style-transitions.json` generated alongside `encoding-plan.json` with time-series array of decision objects
2. Each object includes: `timestamp_s`, `style_applied`, `reason`, `source_signals`, `frame_reference`
3. Human-readable summary generated as part of assembly report
4. Telegram delivery includes style decision summary (e.g., "Split→PiP at 0:42 — camera switched to close-up")
5. Journal is a debug/QA tool first, user-facing second

---

#### Story 13-3: Auto-Style Intelligence

**Slug:** `13-3-auto-style-intelligence`
**Phase:** 6
**Mapped Ideas:** #18, #35, #36, #42, #46, #54
**User-Preferred:** #18 (Auto-style based on content)

**Scope:** Multi-signal layout scoring engine: score each candidate style per segment across face count, text density, motion level, speaker activity, and mood category from `content.json`. User preference (`--style pip`) adds weight to scoring rather than forcing override. Platform-aware output adjustments (Reels vs Shorts vs LinkedIn aspect ratios). Fuses VTT + face detection + frame diff + content analysis signals.

**Acceptance Criteria:**
1. `style=auto` triggers multi-signal scoring instead of fixed style assignment
2. Scoring model weights at least 4 signals: face count, speaker activity, motion, mood
3. User preference acts as weight multiplier, not hard override
4. Selected style per segment logged in `style-transitions.json` with individual signal scores
5. Platform-aware output dimensions configurable (9:16, 1:1, 16:9)

---

#### Story 13-4: Advanced Visual Effects & Content Enhancements

**Slug:** `13-4-advanced-visual-effects`
**Phase:** 7
**Mapped Ideas:** #13, #24, #25, #27, #28, #29, #30, #38
**User-Preferred:** #24 (Animated transitions via xfade)

**Scope:** Animated transitions between style phases using FFmpeg `xfade` filter. Audio waveform visualization bar showing speaking energy per speaker. Screen share OCR via Tesseract for content context. Quote card overlays with impactful transcript quotes. Speaker name labels as lower-third graphics. Border/divider styling with accent colors. Solo speaker cinematic (letterbox + vignette + ken-burns pan). B-roll cutaway slots for Veo3-generated clips.

**Acceptance Criteria:**
1. `xfade` transitions available between style phases (fade, slide, wipe)
2. Audio waveform visualization renders as overlay bar showing per-speaker energy
3. Tesseract OCR extracts text from screen share frames, saved to `screen-share-ocr.json`
4. Speaker name labels rendered as lower-third overlays from research data
5. Border/divider styling configurable per style (color, thickness, rounded corners)

---

#### Story 13-5: Style Gallery Preview

**Slug:** `13-5-style-gallery-preview`
**Phase:** User Interaction
**Mapped Ideas:** #17, #47
**User-Preferred:** #17 (Style gallery preview)

**Scope:** Generate 5-second preview clips for each available style using a sample segment from the current video. Send as Telegram photo/video gallery so user can visually compare styles before committing. Auto-select best thumbnail frame from final reel based on face visibility and composition scoring.

**Acceptance Criteria:**
1. Preview generation produces one 5-second clip per available style from the source video
2. Previews sent as Telegram media group (photo gallery or video clips)
3. User can select preferred style from gallery before full pipeline run
4. Thumbnail auto-selection picks frame with best face visibility and composition
5. Preview generation completes in <60s on Pi (one decode pass, multiple filter chains)

---

### Deferred to Future Backlog

Ideas that represent long-term strategic vision beyond the current 2-epic scope:

| Idea | Description | Why Deferred |
|------|-------------|--------------|
| #41 | Podcast DNA Fingerprint — learn show patterns over multiple runs | Requires multi-run persistence layer not yet built |
| #43 | Open Framing Protocol — `framing-spec.json` shareable schema | Premature standardization before core styles mature |
| #44 | Creator Style Marketplace — community style presets | Requires user ecosystem beyond single-user pipeline |

---

### Idea-to-Story Mapping (Complete)

| Story | Ideas Mapped | Count |
|-------|-------------|-------|
| 12-1 Style Selection Passthrough | #15, #16, #20, #48, #63 | 5 |
| 12-2 Horizontal Split-Screen | #1, #4, #5, #6, #8, #14, #21, #22, #26, #49, #56, #58 | 12 |
| 12-3 PiP Overlay | #2, #3, #7, #12, #23, #50, #55, #60 | 8 |
| 12-4 Pi Benchmark Gate | #62, #65 | 2 |
| 12-5 Screen Share Detection | #31, #34, #37, #39, #40, #51, #57, #59 | 8 |
| 13-1 Dynamic Style FSM | #9, #10, #11, #19, #33, #52, #61, #64 | 8 |
| 13-2 Style Transitions Journal | #32, #45, #53 | 3 |
| 13-3 Auto-Style Intelligence | #18, #35, #36, #42, #46, #54 | 6 |
| 13-4 Advanced Visual Effects | #13, #24, #25, #27, #28, #29, #30, #38 | 8 |
| 13-5 Style Gallery Preview | #17, #47 | 2 |
| **Deferred** | #41, #43, #44 | 3 |
| **Total** | | **65** |

### Priority Order

**Critical Path** (must be sequential):
1. 12-1 → 12-2 → 12-3 → **12-4 (gate)** → 12-5

**Can Parallelize After Gate:**
- 13-1 + 13-5 (independent)
- 13-2 depends on 13-1 (needs FSM decisions to journal)
- 13-3 depends on 13-1 (needs FSM for auto-selection)
- 13-4 can start independently (visual effects are additive)

### User-Preferred Ideas Landing

| Idea | Story | Phase |
|------|-------|-------|
| #16 Natural language style | 12-1 | Phase 0 (earliest) |
| #17 Style gallery preview | 13-5 | Phase 7 |
| #18 Auto-style based on content | 13-3 | Phase 6 |
| #19 Style mixing within a Reel | 13-1 | Phase 4 |
| #24 Animated transitions (xfade) | 13-4 | Phase 7 |
| #45 Decision explanation | 13-2 | Phase 5 |

## Epic Structure Validation (Multi-Model Consensus)

### Models Consulted
- **Gemini 2.5 Pro (Advocate):** 9/10 confidence
- **Gemini 2.5 Flash (Devil's Advocate):** Harsh critique with 4 CRITICAL, 3 HIGH, 2 MEDIUM, 1 LOW findings

### Points of Agreement
1. Epic 12/13 split is correct — core then intelligence
2. Benchmark gate is essential and well-positioned
3. Stories 12-1 through 12-3 are well-scoped for 1-3 days
4. Architecture fit is strong (FramingStyle domain model, FSM in domain layer)
5. User-preferred ideas prioritized correctly in earliest feasible stories

### Critical Findings to Address

**CRITICAL-1: Stories 13-1 and 13-4 are too large**
- 13-1 bundles FSM + focus pull + pulse zoom + spotlight dim + audio sync — each effect is a separate FFmpeg challenge
- 13-4 bundles xfade + OCR + waveform + quote cards + labels + borders + B-roll — at least 3 separate stories
- **Action:** Split 13-1 into FSM-only + visual effects. Split 13-4 into transitions + overlays + OCR

**CRITICAL-2: Dynamic effects + OCR unrealistic on Pi 4**
- Focus pull, pulse zoom, Tesseract OCR on video frames will cripple ARM performance
- **Action:** Flag OCR as Pi-conditional (only if benchmarks show headroom). Simplify dynamic effects to parameter-based (no real-time computation)

**CRITICAL-3: Benchmark gate has no Plan B**
- Binary go/no-go with no tiered fallback
- **Action:** Define 3 tiers: FULL PASS (all styles feasible), PARTIAL PASS (static styles only, no dynamic), FAIL (reduce to core layouts only, defer Epic 13)

**CRITICAL-4: Dynamic filter_complex management**
- Generating complex FFmpeg graphs on-the-fly is high integration risk
- **Action:** Invest in tested FFmpeg command builder with extensive logging. Pre-define filter chain templates rather than dynamic generation

### High Findings

**HIGH-1: 12-5 and 13-3 also too large**
- 12-5 bundles face heuristic + frame diff + presentation mode + whiteboard detection
- 13-3 bundles multi-signal scoring + mood mapping + platform-aware output
- **Action:** Start with simplest heuristics, defer advanced detection. 13-3 starts as rule-based, not ML

**HIGH-2: Simple visual polish buried too deep**
- Borders, speaker labels, divider styling are high-impact but in Phase 7
- **Action:** Move simple overlays (borders, labels) into Epic 12 stories as optional enhancements

**HIGH-3: Vague acceptance criteria**
- "smart corner placement", "presentation mode", "multi-signal scoring" lack testable definitions
- **Action:** Refine all ACs with specific thresholds and algorithms before story creation

### Medium Findings

**MEDIUM-1: 12-5 could parallel 12-2/12-3**
- Screen share detection is Layout Detective work, not FFmpeg-intensive
- **Action:** Consider moving 12-5 before the benchmark gate, parallelizable with 12-2

**MEDIUM-2: Hidden dependencies**
- Motion detection signal doesn't exist yet (needed for 13-3)
- Mood from content.json needs explicit mapping to styles
- **Action:** Add prerequisite for motion signal in 13-3 scope

### Revised Story Count After Splitting

If 13-1 and 13-4 are split as recommended:
- **13-1a** Dynamic Style FSM (static + dynamic switching) — #19, #33, #52
- **13-1b** Dynamic Visual Effects (focus pull, zoom, dim) — #9, #10, #11, #61, #64
- **13-4a** Animated Transitions (xfade) — #24
- **13-4b** Content Overlays (labels, quotes, borders) — #13, #25, #27, #29, #30
- **13-4c** Screen Share OCR + Audio Waveform (Pi-conditional) — #28, #38

This brings Epic 13 to **8 stories** (from 5), total **13 stories** across 2 epics.

## Session Summary

**Key Achievements:**
- 65 ideas generated across 3 brainstorming techniques (Morphological Analysis, SCAMPER, Chaos Engineering)
- Consensus-validated implementation plan with benchmark gate
- 10 implementation stories across 2 epics with complete idea-to-story mapping (13 after consensus splits)
- 6 user-preferred ideas placed in earliest feasible stories
- 3 long-term vision ideas deferred to future backlog
- Clear critical path and parallelization opportunities identified
- Multi-model validation of epic structure with actionable adjustments
