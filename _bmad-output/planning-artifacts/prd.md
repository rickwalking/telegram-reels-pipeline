---
stepsCompleted: [step-01-init, step-02-discovery, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-telegram-reels-pipeline-2026-02-10.md
  - _bmad-output/planning-artifacts/research/technical-telegram-mcp-claude-code-integration-research-2026-02-09.md
  - _bmad-output/brainstorming/brainstorming-session-2026-02-09.md
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 1
  projectDocs: 0
classification:
  projectType: backend_pipeline_service
  domain: content_creation_media_processing
  complexity: medium
  projectContext: greenfield
workflowType: 'prd'
project_name: Telegram Reels Pipeline
user_name: Pedro
date: 2026-02-10
---

# Product Requirements Document - Telegram Reels Pipeline

**Author:** Pedro
**Date:** 2026-02-10

## Executive Summary

**Telegram Reels Pipeline** is an autonomous AI-powered content production system that transforms full-length YouTube podcast episodes into publish-ready Instagram Reels. Triggered by a Telegram message with a URL, the pipeline analyzes the full episode, selects the most compelling moment using contextual understanding, applies intelligent per-segment camera framing, and delivers a near-publishable vertical Reel — complete with descriptions, hashtags, and music suggestions — back to Telegram for review.

**Target user:** Pedro — podcast co-host (LIÇÕEScast) who currently spends ~2 hours per Reel manually, or more often, skips posting entirely when time runs out. The pipeline replaces that 2-hour process with ≤5 minutes of human review.

**Interaction model:** Asynchronous, message-driven. User sends a YouTube URL via Telegram, pipeline processes autonomously on Raspberry Pi, user receives a finished Reel. The only human touchpoints are optional elicitation questions and final review.

**Key differentiators:**
- Context-aware moment selection (narrative understanding, not audio peaks)
- Self-expanding camera layout knowledge base (learns from each escalation)
- Prescriptive multi-agent QA (exact fix instructions, not vague rejections)
- Conversational revision loop (4 revision types via Telegram — no full re-runs)
- BMAD workflow framework repurposed as content pipeline backbone

## Success Criteria

### User Success

| Criteria | Target | Measurement |
|----------|--------|-------------|
| **Camera framing accuracy** | ≥90% of segments require zero manual re-cropping | Segments with correct framing / total segments |
| **Moment selection quality** | Creator genuinely happy to post the selected moment | Reels posted without re-running moment selection |
| **Review time** | ≤5 minutes from delivery to publish-ready decision | Time from Telegram delivery to approval |
| **Publishability rate** | 90-95% near-publishable on first delivery | Reels needing only minor tweaks vs. significant rework |
| **Empowerment feeling** | Pipeline works while Pedro lives his life — delegation, not supervision | Qualitative — zero manual intervention during processing |
| **"Aha moment"** | Pipeline picks the moment Pedro would have chosen, with correct framing | First occurrence within initial 3 runs |

### Business Success

| Criteria | Target | Timeframe |
|----------|--------|-----------|
| **Time reclaimed** | From ~2 hours manual to ≤5 minutes human involvement per Reel | Immediate |
| **Posting consistency** | Content posted after every podcast episode — zero missed | 3 months |
| **Content impact** | Reels generate audience discussion and engagement | Positive trend by month 3 |
| **Knowledge compound effect** | Fewer unknown layouts over time — system learns | 6 months |

### Technical Success

| Criteria | Target | Measurement |
|----------|--------|-------------|
| **End-to-end pipeline time** | ≤20 minutes (goal), ≤45 minutes (acceptable) | Time from URL submission to Telegram delivery |
| **Pipeline completion rate** | ≥90% successful end-to-end runs | Successful runs / total triggered runs |
| **First-pass acceptance rate** | ≥80% approved without re-run | Reels accepted / total generated |
| **Crash recovery** | Auto-resume from last checkpoint after Pi restart | Pipeline resumes without re-processing completed stages |
| **Resource headroom** | Leave sufficient resources for Umbrel services during pipeline runs | Memory cap (e.g., 3GB max), CPU quota (e.g., 80%), FFmpeg thread cap |
| **QA gate effectiveness** | Prescriptive feedback leads to one-shot fixes | Rework cycles per gate (target: ≤1 average) |

### Measurable Outcomes

| KPI | Definition | Target |
|-----|-----------|--------|
| **Post rate** | Episodes with ≥1 Reel published / total episodes | 100% at 3 months |
| **Human time per Reel** | Minutes from delivery to publish-ready | ≤5 minutes |
| **Camera accuracy rate** | Segments with correct framing / total segments | ≥90% |
| **Pipeline speed** | End-to-end execution time | ≤20 min goal, ≤45 min acceptable |
| **Engagement trend** | MoM growth in comments + shares per Reel | Positive by month 3 |

## Product Scope

### MVP — Minimum Viable Product

The complete 7-step autonomous pipeline, scoped to podcast content (see [MVP Feature Set](#mvp-feature-set-phase-1) for full traceability to journeys and success criteria):

- **Telegram trigger** — URL in, optional 2-3 elicitation questions, smart defaults
- **Full episode analysis** — contextual moment selection (narrative, emotional peaks, quotable moments)
- **Camera layout detection** — common LIÇÕEScast layouts (side-by-side, speaker focus, grid) with per-segment crop strategies
- **Layout feedback loop** — unknown layouts flagged for feedback, stored for future runs
- **Video processing** — vertical 9:16 at 1080x1920, FFmpeg on Pi with resource constraints
- **Content generation** — descriptions, hashtags, music suggestions
- **Multi-agent QA** — prescriptive feedback with automatic rework, best-of-three fallback
- **Telegram delivery** — finished Reel + content options back to Telegram
- **Crash recovery** — checkpoint-based resume from last completed stage
- **Single pipeline execution** — one run at a time, FIFO queue for additional requests

### Growth Features (Post-MVP)

- **Saved profiles** — named presets (e.g., "tech-explainer") to skip all elicitation
- **Episode Scanner mode** — send URL with no topic, pipeline identifies top 3 moments and proposes them
- **Gate-by-gate QA decomposition** — separate QA instances per stage with scoped mission briefs
- **Video processing sub-agents** — Layout Detective, FFmpeg Engineer, Assembler as separate agents
- **Multi-Reel per episode** — generate top 2-3 clips per run
- **Self-expanding knowledge base** — automatic layout learning without manual feedback
- **Personal storytelling video support** — swappable agent profiles for non-podcast content

### Vision (Future)

- **Product UI / web dashboard** — dedicated interface for broader user adoption
- **Multi-user support** — authentication, per-user preferences, client management
- **Cross-platform output** — TikTok, YouTube Shorts alongside Instagram Reels
- **Multi-language support** — content generation and captions in multiple languages
- **Content calendar integration** — scheduled posting, batch planning
- **Analytics feedback loop** — learn which Reels perform best and optimize future selection
- **A/B testing** — generate variant Reels for audience testing
- **Series-aware content memory** — track topics across episodes, flag connections

## User Journeys

### Journey 1: Pedro — The Happy Path (Core Experience)

**Opening Scene:** It's Thursday evening. LIÇÕEScast just published a new episode — 1h20m on distributed systems. Pedro is on the couch, phone in hand. In the old days, he'd sigh knowing he needs to watch the entire episode tomorrow, find the best 60 seconds, crop the video, write a caption. Two hours minimum. Tonight, he opens Telegram.

**Rising Action:** Pedro sends the YouTube URL to the bot. Within seconds, the Router Agent responds: "Got it — LIÇÕEScast Tech #14. Any specific topic to focus on, or should I find the best moment?" Pedro types "focus on the CAP theorem debate" and puts his phone down.

The pipeline works silently — researching the episode metadata, analyzing the transcript for the most compelling 60-90 seconds on CAP theorem, detecting that this episode uses side-by-side layout for the debate section, applying the correct crop strategy to frame the active speaker, generating three description options with hashtags.

**Climax:** Twenty minutes later, Pedro's phone buzzes. A finished Reel appears in Telegram — the exact moment where his co-host challenges his take on consistency vs. availability, the camera framing perfectly isolating the speaker, vertical format looking professional. Below it: three caption options, relevant hashtags, and a music suggestion.

**Resolution:** Pedro watches the 70-second Reel, picks description option 2, adjusts one hashtag, and posts to Instagram. Total human time: 3 minutes. He's back on the couch. The episode that would have gone unclipped is now reaching his audience. This is the feeling — empowerment through delegation.

**Requirements revealed:** Telegram trigger, smart elicitation with topic focus, full transcript analysis, camera layout detection, per-segment crop strategy, content generation (descriptions, hashtags, music), Telegram delivery with structured message sequence.

---

### Journey 2: Pedro — Unknown Camera Layout (Escalation & Learning)

**Opening Scene:** A new episode drops — but this time the guest is remote and the production team used a picture-in-picture layout Pedro hasn't seen before. The pipeline starts normally.

**Rising Action:** The Layout Detective agent extracts frames and classifies them. Side-by-side? No. Speaker focus? No. Grid? No. The layout doesn't match any known strategy in the knowledge base. Instead of guessing and producing a badly cropped video, the pipeline pauses.

**Climax:** Pedro receives a Telegram message: "I found a layout I don't recognize. Here's a frame screenshot. How should I crop this? Options: (A) Focus on the main speaker (top-left), (B) Focus on the guest (bottom-right), (C) Custom guidance." Pedro replies "A — focus on the main speaker, he's in the larger frame."

**Resolution:** The pipeline stores this as a new layout strategy — "picture-in-picture, main speaker top-left" — and continues processing. The Reel comes out correctly framed. Next time this layout appears, the system handles it automatically with zero escalation. The knowledge base just grew. Every future run is smarter.

**Requirements revealed:** Frame extraction and classification, unknown layout detection, Telegram escalation with screenshot, user guidance capture, knowledge base storage (crop-strategies.yaml), automatic recognition on subsequent runs.

---

### Journey 3: Pedro — Pipeline Failure & Recovery

**Opening Scene:** Pedro sent a URL an hour ago. He checks Telegram — no Reel delivered. Something's off. He notices Umbrel had a brief power hiccup and the Pi rebooted.

**Rising Action:** The pipeline service auto-starts via systemd. On startup, it checks for in-progress runs. It finds `run-2026-03-15-abc123` with `current_stage: ffmpeg_engineer`, `stages_completed: [router, research, transcript, content, layout_detective]`. Five stages already done. The checkpoint has the session IDs and all intermediate artifacts on disk.

**Climax:** The pipeline resumes from the FFmpeg encoding stage — not from scratch. Pedro receives a Telegram notification: "Resuming your run from video encoding stage (5 of 7 stages already completed)." Ten minutes later, the finished Reel arrives.

**Resolution:** Pedro reviews and posts. He lost maybe 15 minutes total from the crash, not 20+ minutes of a full re-run. The checkpoint system saved the work of five completed agents. He checks the events log later to understand what happened — clear timestamps showing the crash point and recovery.

**Requirements revealed:** Frontmatter checkpoint persistence, session ID storage per agent, systemd auto-restart, crash detection and resume logic, Telegram status notification on recovery, events log for inspection, atomic state writes to prevent corruption.

---

### Journey 4: Pedro — Revision & Feedback Loop

**Opening Scene:** Pedro receives a delivered Reel. He watches it. The moment is good, but something's not quite right — the selected clip cuts off right before his co-host makes the key point that ties the whole argument together. The Reel needs more context.

**Rising Action — Scenario A (Extend moment):** Pedro replies: "Include 15 more seconds before the cut — I need the setup where João explains the tradeoff." The Router Agent interprets this as a moment extension request. The Transcript Agent adjusts timestamps, FFmpeg re-encodes the extended segment with the same crop strategy, QA validates, and a new Reel arrives.

**Rising Action — Scenario B (Fix framing):** On a different occasion, Pedro sees that segment 2 has the wrong speaker in frame during a side-by-side layout. He replies: "Segment 2 framing is wrong — focus on the right speaker, not the left." The Router routes directly to the FFmpeg Engineer with the corrected crop instruction. Only the affected segment is re-processed.

**Rising Action — Scenario C (Different moment):** Pedro watches a Reel and thinks — this moment is fine, but there's a better one around the 45-minute mark. He replies: "Try a different moment — around 45:00 where we discuss event sourcing." The pipeline re-runs moment selection from the transcript, targeting the specified area.

**Rising Action — Scenario D (Add context):** Pedro sees a Reel that jumps straight into a punchline without the setup. He replies: "Include a wider shot of the moment before — I need the context where we set up the problem." The Router interprets this as a context expansion — the Transcript Agent widens the timestamp window, and the pipeline re-processes with the extended segment to give the audience the full story arc.

**Climax:** In each scenario, the Router Agent parses the feedback, identifies which agent needs to act, routes the fix through QA, and delivers only the changed output. No re-reviewing of unchanged content.

**Resolution:** Pedro gets the revised Reel. The feedback loop is natural — conversational in Telegram, just like talking to an editor. The system understands "include more context," "fix the framing," "try a different moment," and "add a wider shot" as distinct revision types.

**Requirements revealed:** Router Agent as feedback interpreter, four revision types (extend moment, fix framing, different moment, add context), targeted agent routing (not full re-run), incremental re-delivery, QA validation on revised output, conversational Telegram interface for revisions.

---

### Journey 5: Pedro — Operations & Maintenance

**Opening Scene:** It's been a month since Pedro started using the pipeline. It's running smoothly, but he wants to check on things — how many runs completed, are there any patterns in QA rejections, is the knowledge base growing?

**Rising Action:** Pedro checks the runs directory — timestamped folders for each run, each with a `run.md` showing the full pipeline history. He sees that 8 out of 9 runs completed successfully, one had a best-of-three override on the FFmpeg gate. He checks `crop-strategies.yaml` — it's grown from 3 to 5 strategies after two escalation-and-learn cycles.

He also notices the Pi's SD card is getting full from accumulated video assets. He runs a cleanup of completed run assets older than 30 days, keeping only the final Reels and run metadata.

**Climax:** Pedro spots that QA gate 3b (FFmpeg encoding) has the most rework cycles. He reads the QA feedback history and realizes the issue is a specific transition type between layouts. He updates the crop strategy parameters for that transition — a 5-minute manual tweak that prevents future rework cycles.

**Resolution:** The system is transparent and inspectable. Pedro can understand what's happening, spot patterns, and make targeted improvements. The file-based state management means everything is readable — no database to query, no dashboard needed. The system appreciates in value as Pedro occasionally tunes it.

**Requirements revealed:** Per-run isolated workspace with inspectable state, human-readable frontmatter and event logs, crop-strategies.yaml as editable knowledge base, disk cleanup strategy for old assets, QA feedback history accessible for pattern analysis, file-based architecture enabling manual inspection.

---

### Journey Requirements Summary

| Capability | Revealed By Journey |
|-----------|-------------------|
| Telegram trigger + smart elicitation | Journey 1 (Happy Path) |
| Full transcript analysis + moment selection | Journey 1, Journey 4C |
| Camera layout detection + crop strategies | Journey 1, Journey 2 |
| Content generation (descriptions, hashtags, music) | Journey 1 |
| Unknown layout escalation + learning | Journey 2 |
| Knowledge base storage + auto-recognition | Journey 2 |
| Checkpoint persistence + crash recovery | Journey 3 |
| Systemd auto-restart + resume logic | Journey 3 |
| Router Agent as feedback interpreter | Journey 4 |
| Four revision types (extend, fix framing, different moment, add context) | Journey 4 |
| Incremental re-delivery (only changed parts) | Journey 4 |
| Per-run workspace with inspectable state | Journey 5 |
| Human-readable logs and configuration | Journey 5 |
| Disk cleanup for old assets | Journey 5 |

## Innovation & Novel Patterns

### Detected Innovation Areas

| Innovation | Description | Competitive Gap Addressed |
|-----------|-------------|--------------------------|
| **Context-aware moment selection** | AI analyzes full episode narrative — topic, structure, emotional peaks, quotable moments — to select genuinely compelling clips. Not audio energy peaks or keyword density | Existing tools (Opus Clip, Vidyo.ai) rely on surface-level signals. This system understands *why* a moment matters in context |
| **Self-expanding layout knowledge base** | Unknown camera layouts trigger a human-in-the-loop learning cycle. Each resolved escalation becomes a permanent new strategy. The system appreciates in value with every run | Existing tools apply fixed cropping rules. This system learns and adapts to any podcast format over time |
| **Prescriptive multi-agent QA** | QA gates provide exact fix instructions with domain knowledge — "detected layout X at timestamp Y, prescribe Strategy B with parameters Z." Not vague "try again" rejections | No comparable system uses prescriptive feedback loops with accumulated domain knowledge for video content QA |
| **BMAD framework as content pipeline backbone** | Repurposing a multi-agent software development framework as the orchestration engine for autonomous content production. Workflow chain as FSM, agents as specialized workers, step files as pipeline stages | Novel application of development workflow patterns to creative content production |

### Validation Approach

| Innovation | Validation Method | Success Signal |
|-----------|------------------|---------------|
| Context-aware selection | Compare pipeline's moment picks against Pedro's manual selections for the same episodes | Pipeline picks moments Pedro would have chosen (or moments he's equally happy to post) |
| Self-expanding knowledge | Track escalation frequency over time — should decrease as knowledge base grows | Second encounter with a previously-unknown layout requires zero human intervention |
| Prescriptive QA | Measure rework cycles per gate — prescriptive feedback should produce one-shot fixes | Average rework cycles ≤1 per gate |
| BMAD as pipeline engine | End-to-end pipeline completion rate and execution time | ≥90% completion rate within 20-45 minute window |

### Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Context-aware selection picks technically correct but editorially boring moments | Low user satisfaction despite pipeline "working" | Pedro's subjective approval as primary metric. Revision journey (Journey 4) provides quick correction path |
| Knowledge base grows with incorrect strategies from bad user feedback | Compounds errors on future runs | QA gate validates output even for known layouts. Bad strategies produce QA failures that surface the issue |
| Prescriptive QA is only as good as the domain knowledge encoded | Blind spots in crop strategy playbook lead to unhelpful prescriptions | Best-of-three fallback + escalation to user when QA can't prescribe a fix |
| BMAD framework wasn't designed for content pipelines | Unexpected workflow limitations at scale | Architecture uses BMAD patterns (FSM, step files, agents) but implemented in Python — not locked to BMAD tooling |

## Backend Pipeline Service Requirements

### Project-Type Overview

Telegram Reels Pipeline is an **autonomous backend pipeline service** — a daemon process running on Raspberry Pi that receives commands via Telegram, executes a multi-agent AI pipeline, and delivers results back via Telegram. There is no web interface, no API, no CLI commands for the user. The entire interaction surface is a Telegram chat.

**Interaction model:** Asynchronous message-driven. User sends a message, pipeline processes autonomously, user receives results. The only synchronous moment is the Router Agent's elicitation questions (0-2 questions via Telegram `ask_user`).

### Technical Architecture Considerations

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Runtime** | Python 3.11+ daemon process | Async-native, Claude Agent SDK support, FFmpeg bindings |
| **Agent orchestration** | BMAD workflow chain as FSM | State Pattern with transition table, checkpoint persistence |
| **Agent execution** | Claude Code CLI (Phase 1) → Agent SDK (Phase 2) | CLI for simplicity, SDK migration for programmatic control |
| **Messaging** | Telegram MCP Server (qpd-v/mcp-communicator-telegram) | `ask_user`, `notify_user`, `send_file` — unified inbound/outbound |
| **Video processing** | FFmpeg with resource constraints | Thread cap (`-threads 2`), memory guard, thermal throttle check |
| **Video download** | yt-dlp | Metadata extraction, subtitle download, video download |
| **QA model dispatch** | PAL MCP (multi-model) | Route QA to Gemini/o4-mini for cost efficiency |
| **State persistence** | File-based (markdown frontmatter + JSON) | BMAD-native, human-readable, crash-recoverable |
| **Queue management** | File-based FIFO with flock | Single-consumer, dedup by Telegram update_id |
| **Process management** | systemd service | Auto-start, auto-restart, watchdog, resource limits |

### Configuration Architecture

| Config Type | Method | Contents |
|------------|--------|----------|
| **Secrets** | Environment variables (`.env` file loaded by systemd) | `TELEGRAM_TOKEN`, `CHAT_ID`, `ANTHROPIC_API_KEY`, Google Drive credentials |
| **Pipeline settings** | YAML (`config/pipeline.yaml`) | Timeframe targets, QA thresholds, FFmpeg parameters, model routing table, max attempts per gate |
| **Crop strategies** | YAML (`config/crop-strategies.yaml`) | Layout definitions, crop regions, strategy parameters — self-expanding via feedback loop |
| **User profiles** | YAML (`config/profiles.yaml`) | Named presets with default elicitation values (Growth feature) |
| **Quality gates** | YAML (`config/quality-gates.yaml`) | Per-gate validation criteria, scoring thresholds, blocker severity definitions |

### Deployment Architecture

```
Raspberry Pi (Umbrel)
├── systemd service: telegram-reels-pipeline
│   ├── ExecStart: python3 -m pipeline.app.main
│   ├── Restart: always (RestartSec=30)
│   ├── MemoryMax: 3G
│   ├── CPUQuota: 80%
│   └── Environment: loaded from /etc/telegram-reels-pipeline/env
├── MCP servers (spawned per pipeline run)
│   ├── telegram MCP (qpd-v/mcp-communicator-telegram)
│   └── PAL MCP (multi-model dispatch)
├── workspace: /home/umbrel/pipeline/
│   ├── config/          (YAML configuration files)
│   ├── runs/            (per-run isolated workspaces)
│   ├── queue/           (FIFO inbox/processing/completed)
│   └── knowledge/       (self-expanding layout knowledge base)
└── tools: ffmpeg, yt-dlp (system-installed)
```

### Implementation Considerations

- **Single pipeline execution** — one active run at a time. FIFO queue with Telegram notifications for position
- **Resource awareness** — check available memory and thermal state before starting FFmpeg. Back off if Pi is under stress
- **Disk management** — video assets stored in tmpfs where possible to reduce SD card wear. Completed run assets cleaned after 30 days
- **Graceful shutdown** — on SIGTERM, checkpoint current state and exit cleanly. Resume on next start
- **Logging** — append-only event journal per run + structured frontmatter checkpoints. No external logging service needed
- **Monitoring** — systemd watchdog (WatchdogSec=300). Pipeline sends heartbeat. Stale process auto-restarted

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — the minimum that delivers end-to-end value: send a URL, receive a publishable Reel with the ability to request revisions.

**Resource Requirements:** Solo developer (Pedro), Raspberry Pi infrastructure, Claude MAX subscription, Telegram bot. No team, no cloud infrastructure, no external dependencies beyond API access.

**All 5 user journeys are MVP-essential:**

| Journey | MVP Justification |
|---------|------------------|
| Journey 1 (Happy Path) | Core value — without this, no product |
| Journey 2 (Unknown Layout) | First unknown layout = broken pipeline without escalation |
| Journey 3 (Crash Recovery) | Pi reliability demands checkpoint resume — re-running from scratch wastes 20+ minutes |
| Journey 4 (Revision Loop) | Re-triggering full runs for minor fixes burns time and tokens. Targeted revisions are essential for ≤5 min review target |
| Journey 5 (Operations) | File-based state is inherent to architecture. Manual inspection and cleanup needed from day one |

### MVP Feature Set (Phase 1)

**Must-Have Capabilities:**

| # | Capability | Journey Source | Success Criteria Linked |
|---|-----------|---------------|------------------------|
| 1 | Telegram trigger with smart elicitation (0-2 questions, smart defaults) | J1 | Empowerment — zero-friction trigger |
| 2 | Full episode analysis with contextual moment selection | J1 | Moment selection quality ≥ subjective approval |
| 3 | Camera layout detection for common LIÇÕEScast layouts | J1, J2 | Camera accuracy ≥90% |
| 4 | Unknown layout escalation with screenshot + learning | J2 | Knowledge compound effect |
| 5 | Video processing (9:16, 1080x1920, FFmpeg on Pi) | J1 | Pipeline speed ≤20 min goal |
| 6 | Content generation (3 description options, hashtags, music suggestion) | J1 | Publishability rate 90-95% |
| 7 | Multi-agent QA with prescriptive feedback + best-of-three | J1 | First-pass acceptance ≥80% |
| 8 | Telegram delivery (video + content options) | J1 | Human time per Reel ≤5 min |
| 9 | Revision loop — 4 types: extend moment, fix framing, different moment, add context | J4 | Review time ≤5 min |
| 10 | Checkpoint persistence + crash recovery + auto-resume | J3 | Crash recovery — resume without re-processing |
| 11 | Single pipeline execution with FIFO queue | J1, J3 | Pipeline completion rate ≥90% |
| 12 | Per-run isolated workspace with inspectable state | J5 | Human-readable operations |
| 13 | Resource-aware execution (memory cap, CPU quota, thermal check) | J5 | Leave headroom for Umbrel |

### Post-MVP Features

**Phase 2 (Growth):**

| # | Feature | Dependency | Value Add |
|---|---------|-----------|-----------|
| 1 | Saved profiles (skip all elicitation) | MVP stable | Zero-friction repeated use |
| 2 | Episode Scanner mode (top 3 moments proposed) | MVP moment selection proven | Removes last manual decision |
| 3 | Gate-by-gate QA decomposition (scoped mission briefs) | MVP QA validated | More precise quality control |
| 4 | Video processing sub-agents (Layout Detective, FFmpeg Engineer, Assembler) | MVP video processing stable | Better separation of concerns, parallel processing |
| 5 | Multi-Reel per episode (top 2-3 clips) | MVP single Reel proven | More content per episode |
| 6 | Automatic layout learning (no manual feedback) | MVP feedback loop proven | Reduce escalations to zero |
| 7 | Agent SDK migration (from CLI to programmatic) | MVP CLI backend stable | Better error handling, session control |

**Phase 3 (Expansion):**

| # | Feature | Value Add |
|---|---------|-----------|
| 1 | Personal storytelling video support | New content format via swappable agent profiles |
| 2 | Product UI / web dashboard | Broader user adoption beyond Pedro |
| 3 | Multi-user support | Authentication, per-user preferences |
| 4 | Cross-platform output (TikTok, YouTube Shorts) | Reach more audiences |
| 5 | Content calendar integration | Scheduled posting, batch planning |
| 6 | Analytics feedback loop | Learn which Reels perform best |
| 7 | A/B testing + series-aware content memory | Advanced optimization |

### Risk Mitigation Strategy

**Technical Risks:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| 20-minute target not achievable on Pi | Medium | Low (45 min acceptable) | Profile each stage. FFmpeg encoding likely bottleneck — optimize thread allocation and encoding params first |
| Claude API instability during long runs | Low | Medium | Checkpoint per stage. Recovery chain retries → fork → fresh session. No single API call is catastrophic |
| FFmpeg encoding produces artifacts on Pi ARM | Low | Medium | QA gate with frame validation catches issues before delivery. Prescriptive fixes target exact FFmpeg params |
| Context window exceeded for long episodes (2h+) | Medium | Medium | Chunk transcript analysis. Research agent summarizes metadata first, transcript agent works on relevant sections only |

**Market Risks:**

| Risk | Mitigation |
|------|-----------|
| Moment selection doesn't match Pedro's editorial judgment | Revision loop (Journey 4) provides immediate correction. Each correction teaches the system what "good" looks like |
| Pipeline produces content Pedro wouldn't post | 90-95% publishability target acknowledges imperfection. Best-of-three QA + revision loop as safety net |

**Resource Risks:**

| Risk | Mitigation |
|------|-----------|
| Solo developer — Pedro is both user and builder | BMAD framework structures the work. Each phase is independently valuable. No phase depends on completing all of the next |
| Pi hardware insufficient | Single pipeline execution respects constraints. If Pi truly can't handle FFmpeg, cloud encoding (e.g., Lambda) is a surgical fix that doesn't change the architecture |

## Functional Requirements

### Trigger & Elicitation

- **FR1:** User can trigger a pipeline run by sending a YouTube URL via Telegram message
- **FR2:** System can ask the user 0-2 targeted elicitation questions (topic focus, duration preference, specific moment) via Telegram
- **FR3:** System can proceed with predefined defaults from pipeline configuration when the user provides only a URL and no additional context
- **FR4:** System can notify the user of their queue position when a run is already in progress

### Episode Analysis & Moment Selection

- **FR5:** System can extract video metadata (title, duration, channel, publish date) from a YouTube URL
- **FR6:** System can download and parse episode subtitles/transcripts
- **FR7:** System can analyze the full transcript to identify highest-scoring moments based on narrative structure score, emotional peak detection, and quotable statement density
- **FR8:** System can focus moment selection on a user-specified topic when provided
- **FR9:** System can select a 60-90 second segment that is highest-scoring by moment selection criteria within the episode's subject matter

### Camera Layout & Video Processing

- **FR10:** System can extract frames from the source video at key timestamps
- **FR11:** System can detect and classify camera layouts (side-by-side, speaker focus, grid) from extracted frames
- **FR12:** System can apply per-segment crop strategies based on detected layout to produce vertical 9:16 video at 1080x1920
- **FR13:** System can handle layout transitions within a single segment by splitting at frame boundaries
- **FR14:** System can escalate unknown camera layouts to the user via Telegram with a screenshot for guidance
- **FR15:** System can store user-provided layout guidance as a new crop strategy in the knowledge base
- **FR16:** System can automatically recognize previously-learned layouts in future runs without user intervention

### Content Generation

- **FR17:** System can generate 3 Instagram description options relevant to the selected moment
- **FR18:** System can generate relevant hashtags for the selected moment
- **FR19:** System can suggest background music matching the detected content mood category

### Quality Assurance

- **FR20:** System can validate each pipeline stage output against defined quality criteria before proceeding
- **FR21:** System can provide prescriptive feedback with exact fix instructions when a QA gate rejects an artifact
- **FR22:** System can automatically rework a rejected artifact using prescriptive QA feedback
- **FR23:** System can select the best attempt after 3 QA failures using score-based comparison (best-of-three)
- **FR24:** System can escalate to the user via Telegram when all automated QA recovery is exhausted

### Delivery & Review

- **FR25:** System can deliver the finished Reel video via Telegram
- **FR26:** System can deliver description options, hashtags, and music suggestions as structured Telegram messages alongside the video
- **FR27:** System can upload videos exceeding 50MB to Google Drive and deliver the link via Telegram
- **FR28:** User can approve the delivered Reel and proceed to publish

### Revision & Feedback

- **FR29:** User can request a moment extension (include more seconds before/after the selected clip for context)
- **FR30:** User can request a framing fix on a specific segment (change which speaker is in frame)
- **FR31:** User can request a different moment entirely (specify approximate timestamp or topic)
- **FR32:** User can request additional context (wider/longer shot of a specific moment)
- **FR33:** System can interpret revision feedback and route to the appropriate pipeline agent without re-running the full pipeline
- **FR34:** System can re-deliver only the changed output after a revision (incremental re-delivery)

### State Management & Recovery

- **FR35:** System can persist pipeline state as checkpoints after each completed stage
- **FR36:** System can detect an interrupted run on startup and resume from the last completed checkpoint
- **FR37:** System can notify the user via Telegram when resuming an interrupted run
- **FR38:** System can maintain per-run isolated workspaces with all artifacts and metadata
- **FR39:** System can enforce single-pipeline execution with a FIFO queue for additional requests

### Operations & Maintenance

- **FR40:** System can store pipeline run history in human-readable format (markdown frontmatter, event logs)
- **FR41:** System can auto-start on Pi boot and auto-restart after crashes via the process manager
- **FR42:** System can monitor resource usage (memory, CPU, thermal) and defer processing when the Pi is under stress
- **FR43:** User can inspect run history, QA feedback, and knowledge base through the filesystem

## Non-Functional Requirements

### Performance

| NFR | Target | Measurement |
|-----|--------|-------------|
| **NFR-P1:** End-to-end pipeline execution time | ≤20 min (goal), ≤45 min (acceptable) | Wall-clock time from URL submission to Telegram delivery |
| **NFR-P2:** FFmpeg encoding time for a 90-second segment | ≤5 minutes on Pi ARM | Encoding stage duration in run event log |
| **NFR-P3:** Telegram message response latency (elicitation) | ≤3 seconds from user reply to pipeline acknowledgment | Time between Telegram update received and agent response |
| **NFR-P4:** Memory usage during FFmpeg encoding | ≤3GB peak (leave headroom for Umbrel) | systemd MemoryMax enforcement + pipeline memory monitoring |
| **NFR-P5:** CPU usage during FFmpeg encoding | ≤80% of available cores | systemd CPUQuota + FFmpeg `-threads` cap |
| **NFR-P6:** Disk I/O for video processing | Use tmpfs where possible to reduce SD card wear | Video intermediates written to RAM-backed storage |

### Reliability

| NFR | Target | Measurement |
|-----|--------|-------------|
| **NFR-R1:** Pipeline completion rate | ≥90% successful end-to-end runs | Successful runs / total triggered runs |
| **NFR-R2:** Crash recovery — resume from checkpoint | Resume within 60 seconds of restart, from last completed stage | Time from systemd restart to pipeline resume |
| **NFR-R3:** State persistence atomicity | Zero corrupted checkpoint files after unexpected shutdown | Atomic writes (write-to-temp + rename) for all state files |
| **NFR-R4:** Service auto-restart after crash | ≤30 seconds from process exit to restart | systemd RestartSec=30, Restart=always |
| **NFR-R5:** Watchdog heartbeat | Pipeline sends heartbeat every ≤5 minutes during active processing | systemd WatchdogSec=300, stale process auto-killed and restarted |
| **NFR-R6:** QA rework convergence | ≤1 average rework cycle per gate; hard cap at 3 attempts | Rework count per gate in run event log |

### Integration

| NFR | Target | Measurement |
|-----|--------|-------------|
| **NFR-I1:** Telegram video delivery | Handle ≤50MB inline; auto-redirect to Google Drive for larger files | Delivery method logged per run |
| **NFR-I2:** Telegram Bot API rate limits | Respect rate limits (30 messages/sec global, 1 msg/sec per chat) with backoff | Zero 429 errors in production |
| **NFR-I3:** YouTube video download resilience | Handle yt-dlp failures gracefully — retry up to 3 times with exponential backoff | Download success rate ≥98% |
| **NFR-I4:** Claude API session management | Each agent stage runs in an independent session; no cross-stage context dependency | Session isolation verified via checkpoint design |
| **NFR-I5:** MCP server lifecycle | MCP servers (Telegram, PAL) spawned per pipeline run and cleanly terminated on completion | Zero orphaned MCP processes after run completion |
| **NFR-I6:** External dependency failure notification | User notified via Telegram within 60 seconds when a critical external service is unreachable | Notification sent for YouTube, Claude API, Google Drive failures |

### Security

| NFR | Target | Measurement |
|-----|--------|-------------|
| **NFR-S1:** API credentials stored as environment variables | Zero secrets in configuration files, code, or version control | Secrets loaded from .env via systemd EnvironmentFile |
| **NFR-S2:** Telegram CHAT_ID validation | Only process messages from authorized CHAT_ID | Unauthorized messages logged and silently ignored |
| **NFR-S3:** File permissions for configuration and state | Config and state files readable only by pipeline service user | File permissions set to 600/700 on sensitive paths |
| **NFR-S4:** No external network exposure | Pipeline is inbound-only via Telegram polling — no open ports, no HTTP server | Zero listening sockets in production |
