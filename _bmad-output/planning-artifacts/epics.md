---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
status: 'complete'
completedAt: '2026-02-10'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# Telegram Reels Pipeline - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Telegram Reels Pipeline, decomposing the requirements from the PRD and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can trigger a pipeline run by sending a YouTube URL via Telegram message
FR2: System can ask the user 0-2 targeted elicitation questions (topic focus, duration preference, specific moment) via Telegram
FR3: System can proceed with predefined defaults from pipeline configuration when the user provides only a URL and no additional context
FR4: System can notify the user of their queue position when a run is already in progress
FR5: System can extract video metadata (title, duration, channel, publish date) from a YouTube URL
FR6: System can download and parse episode subtitles/transcripts
FR7: System can analyze the full transcript to identify highest-scoring moments based on narrative structure score, emotional peak detection, and quotable statement density
FR8: System can focus moment selection on a user-specified topic when provided
FR9: System can select a 60-90 second segment that is highest-scoring by moment selection criteria within the episode's subject matter
FR10: System can extract frames from the source video at key timestamps
FR11: System can detect and classify camera layouts (side-by-side, speaker focus, grid) from extracted frames
FR12: System can apply per-segment crop strategies based on detected layout to produce vertical 9:16 video at 1080x1920
FR13: System can handle layout transitions within a single segment by splitting at frame boundaries
FR14: System can escalate unknown camera layouts to the user via Telegram with a screenshot for guidance
FR15: System can store user-provided layout guidance as a new crop strategy in the knowledge base
FR16: System can automatically recognize previously-learned layouts in future runs without user intervention
FR17: System can generate 3 Instagram description options relevant to the selected moment
FR18: System can generate relevant hashtags for the selected moment
FR19: System can suggest background music matching the detected content mood category
FR20: System can validate each pipeline stage output against defined quality criteria before proceeding
FR21: System can provide prescriptive feedback with exact fix instructions when a QA gate rejects an artifact
FR22: System can automatically rework a rejected artifact using prescriptive QA feedback
FR23: System can select the best attempt after 3 QA failures using score-based comparison (best-of-three)
FR24: System can escalate to the user via Telegram when all automated QA recovery is exhausted
FR25: System can deliver the finished Reel video via Telegram
FR26: System can deliver description options, hashtags, and music suggestions as structured Telegram messages alongside the video
FR27: System can upload videos exceeding 50MB to Google Drive and deliver the link via Telegram
FR28: User can approve the delivered Reel and proceed to publish
FR29: User can request a moment extension (include more seconds before/after the selected clip for context)
FR30: User can request a framing fix on a specific segment (change which speaker is in frame)
FR31: User can request a different moment entirely (specify approximate timestamp or topic)
FR32: User can request additional context (wider/longer shot of a specific moment)
FR33: System can interpret revision feedback and route to the appropriate pipeline agent without re-running the full pipeline
FR34: System can re-deliver only the changed output after a revision (incremental re-delivery)
FR35: System can persist pipeline state as checkpoints after each completed stage
FR36: System can detect an interrupted run on startup and resume from the last completed checkpoint
FR37: System can notify the user via Telegram when resuming an interrupted run
FR38: System can maintain per-run isolated workspaces with all artifacts and metadata
FR39: System can enforce single-pipeline execution with a FIFO queue for additional requests
FR40: System can store pipeline run history in human-readable format (markdown frontmatter, event logs)
FR41: System can auto-start on Pi boot and auto-restart after crashes via the process manager
FR42: System can monitor resource usage (memory, CPU, thermal) and defer processing when the Pi is under stress
FR43: User can inspect run history, QA feedback, and knowledge base through the filesystem
FR-AI1: User can pass additional instructions via a CLI flag (e.g., --instructions) containing free-form text with creative directives for the short
FR-AI2: Router agent can parse additional instructions and extract structured directive categories: overlay images, cutaway video clips, transition effects, and narrative overrides
FR-AI3: Router agent can validate referenced media files (images, videos) exist and are accessible before forwarding to downstream agents
FR-AI4: Router agent can produce structured directive fields in router-output.json that downstream agents consume (overlay_images, cutaway_clips, transition_preferences, narrative_overrides)
FR-AI5: Content Creator agent can consume narrative override directives to adjust tone, structure, pacing, and story arc of the generated content
FR-AI6: FFmpeg Engineer agent can consume transition effect directives to apply user-specified transitions (wipes, fades, custom effects) to segments
FR-AI7: FFmpeg Engineer agent can consume overlay image directives to insert user-provided images at specified moments in the short
FR-AI8: Assembly stage can incorporate user-provided video clips as documentary-style cutaways, integrating with the existing B-roll/cutaway system (Epic 20)

### NonFunctional Requirements

NFR-P1: End-to-end pipeline execution time ≤20 min (goal), ≤45 min (acceptable)
NFR-P2: FFmpeg encoding time for a 90-second segment ≤5 minutes on Pi ARM
NFR-P3: Telegram message response latency (elicitation) ≤3 seconds
NFR-P4: Memory usage during FFmpeg encoding ≤3GB peak
NFR-P5: CPU usage during FFmpeg encoding ≤80% of available cores
NFR-P6: Disk I/O for video processing — use tmpfs where possible
NFR-R1: Pipeline completion rate ≥90% successful end-to-end runs
NFR-R2: Crash recovery — resume within 60 seconds of restart
NFR-R3: State persistence atomicity — zero corrupted checkpoint files
NFR-R4: Service auto-restart after crash ≤30 seconds
NFR-R5: Watchdog heartbeat every ≤5 minutes during active processing
NFR-R6: QA rework convergence ≤1 average rework cycle per gate; hard cap at 3 attempts
NFR-I1: Telegram video delivery — handle ≤50MB inline; auto-redirect to Google Drive for larger
NFR-I2: Telegram Bot API rate limits — respect with backoff, zero 429 errors
NFR-I3: YouTube video download resilience — retry up to 3 times with exponential backoff
NFR-I4: Claude API session management — independent sessions per stage
NFR-I5: MCP server lifecycle — spawned per run, cleanly terminated on completion
NFR-I6: External dependency failure notification within 60 seconds
NFR-S1: API credentials stored as environment variables, zero secrets in code
NFR-S2: Telegram CHAT_ID validation — only process authorized messages
NFR-S3: File permissions 600/700 on sensitive paths
NFR-S4: No external network exposure — Telegram polling only, zero open ports
NFR-AI1: Additional instructions parsing must not add more than 2 seconds to Router agent execution time
NFR-AI2: Media file validation (existence, format, size) must happen at the Router stage to fail fast before expensive downstream processing

### Additional Requirements

**From Architecture — Starter Template & Scaffolding:**
- Manual scaffolding with Poetry (`poetry init`, `poetry add`) — no starter template. This is Epic 1 Story 1
- Hexagonal Architecture with 4 layers: Domain → Application → Infrastructure → Composition Root
- 8 Port Protocols defined as Python Protocols: AgentExecutionPort, ModelDispatchPort, MessagingPort, VideoProcessingPort, VideoDownloadPort, StateStorePort, FileDeliveryPort, KnowledgeBasePort

**From Architecture — Implementation Sequence (10 steps):**
1. Domain types, entities, Port Protocols (zero external deps)
2. FSM state machine + transitions + guards
3. File-based state persistence (frontmatter read/write, atomic ops)
4. Agent executor (CLI backend first)
5. QA reflection loop (single-model)
6. EventBus + listeners (journal, checkpoint, Telegram notifier)
7. Recovery chain (levels 1-3 + 6)
8. Queue consumer (FIFO + flock)
9. Workspace manager (factory + context manager)
10. Composition root (bootstrap + settings + main)

**From Architecture — BMAD Workflow Layer:**
- workflow.md entrypoint + 8 stage step files (stage-01-router through stage-08-delivery)
- 8 agent definitions with persona + knowledge files
- 7 QA gate criteria files + QA gate template
- 4 revision flow files (extend-moment, fix-framing, different-moment, add-context)

**From Architecture — Infrastructure & Deployment:**
- systemd service configuration (unit file, env file)
- Poetry for all dependency management
- Tooling: black (120), isort (black profile), ruff (py311), mypy --strict, pytest (asyncio, 80% coverage)
- .editorconfig, pyproject.toml as single config, .env for secrets

**From Architecture — Pattern Enforcement:**
- Hexagonal import rules enforced (domain: stdlib only)
- Atomic write pattern for all state mutations
- Pydantic-validated QA critique schema
- Event naming convention (snake_case, dot-namespaced, past tense)
- Frontmatter schema for run.md (exact fields defined)

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 2 | Telegram URL trigger |
| FR2 | Epic 2 | Elicitation questions |
| FR3 | Epic 2 | Smart defaults |
| FR4 | Epic 2 | Queue position notification |
| FR5 | Epic 2 | Video metadata extraction |
| FR6 | Epic 2 | Subtitle/transcript download |
| FR7 | Epic 2 | Transcript analysis + moment scoring |
| FR8 | Epic 2 | Topic-focused moment selection |
| FR9 | Epic 2 | 60-90 second segment selection |
| FR10 | Epic 3 | Frame extraction at timestamps |
| FR11 | Epic 3 | Camera layout classification |
| FR12 | Epic 3 | Per-segment crop + vertical output |
| FR13 | Epic 3 | Layout transition handling |
| FR14 | Epic 3 | Unknown layout escalation |
| FR15 | Epic 3 | Layout learning + knowledge base storage |
| FR16 | Epic 3 | Auto-recognition of learned layouts |
| FR17 | Epic 4 | 3 description options |
| FR18 | Epic 4 | Hashtag generation |
| FR19 | Epic 4 | Music suggestion |
| FR20 | Epic 1 | QA gate validation per stage |
| FR21 | Epic 1 | Prescriptive QA feedback |
| FR22 | Epic 1 | Automatic rework from QA feedback |
| FR23 | Epic 1 | Best-of-three selection |
| FR24 | Epic 1 | User escalation when QA exhausted |
| FR25 | Epic 4 | Deliver Reel via Telegram |
| FR26 | Epic 4 | Deliver content options alongside video |
| FR27 | Epic 4 | Google Drive upload for >50MB |
| FR28 | Epic 4 | User approval flow |
| FR29 | Epic 5 | Moment extension revision |
| FR30 | Epic 5 | Framing fix revision |
| FR31 | Epic 5 | Different moment revision |
| FR32 | Epic 5 | Add context revision |
| FR33 | Epic 5 | Feedback interpretation + routing |
| FR34 | Epic 5 | Incremental re-delivery |
| FR35 | Epic 1 | Checkpoint persistence |
| FR36 | Epic 6 | Crash detection + resume |
| FR37 | Epic 6 | Resume notification |
| FR38 | Epic 1 | Per-run isolated workspaces |
| FR39 | Epic 1 | Single execution + FIFO queue |
| FR40 | Epic 1 | Human-readable run history |
| FR41 | Epic 6 | Auto-start + auto-restart |
| FR42 | Epic 6 | Resource monitoring |
| FR43 | Epic 6 | Filesystem inspection |
| FR44 | Epic 17 | Extended Veo3Prompt with narrative_anchor, duration_s, idempotent_key |
| FR45 | Epic 17 | Veo3Job + Veo3JobStatus domain models for job tracking |
| FR46 | Epic 17 | VideoGenerationPort protocol (9th port) |
| FR47 | Epic 17 | GeminiVeo3Adapter implementation (Gemini API integration) |
| FR48 | Epic 17 | Async parallel generation with idempotent keys |
| FR49 | Epic 17 | Polling worker with adaptive backoff |
| FR50 | Epic 17 | Await gate blocking before Stage 7 |
| FR51 | Epic 17 | Per-clip status tracking (partial success) |
| FR52 | Epic 17 | Content Creator enriched veo3_prompts with placement + style |
| FR53 | Epic 17 | Narrative anchor placement (story language, not timestamps) |
| FR54 | Epic 17 | Assembly variant-driven insertion logic |
| FR55 | Epic 17 | Documentary cutaway model (silent video over continuous audio) |
| FR56 | Epic 17 | Always-crop watermark post-processing |
| FR57 | Epic 17 | Configurable settings (VEO3_CLIP_COUNT, VEO3_TIMEOUT_S, VEO3_CROP_BOTTOM_PX) |
| FR58 | Epic 17 | Clip quality validation (resolution, duration, black-frame) |
| FR59 | Epic 17 | Semantic/fuzzy narrative anchor matching with skip fallback |
| FR60 | Epic 18 | Veo3 duration_seconds must use even values only (4/6/8) |
| FR61 | Epic 18 | Rate limit handling with exponential backoff and sequential submission |
| FR62 | Epic 18 | Authenticated video download via Gemini Files API URI + API key |
| FR63 | Epic 18 | Auto-retry failed Veo3 jobs in await gate (transient vs permanent failure) |
| FR64 | Epic 18 | dispatch_timeout_seconds wired through CLI and bootstrap |
| FR65 | Epic 19 | Two-pass B-roll overlay assembly (base reel then overlay pass) |
| FR66 | Epic 19 | Auto-upscale B-roll clips to match segment dimensions (1080x1920) |
| FR67 | Epic 19 | PTS-offset overlay technique for correct timeline placement |
| FR68 | Epic 19 | Assembly QA validation for B-roll visual presence and opacity |
| FR69 | Epic 20 | Download external video clips (YouTube Shorts, arbitrary URLs) via yt-dlp |
| FR70 | Epic 20 | Content Creator agent auto-discovers relevant external reference clips |
| FR71 | Epic 20 | CLI --cutaway flag for user-provided external clip URLs with timestamps |
| FR72 | Epic 20 | Unified B-roll manifest merging Veo3 clips and external documentary clips |
| FR73 | Epic 20 | Narrative anchor matching for external clips (transcript timestamp mapping) |
| FR-AI1 | Epic 21 | CLI --instructions flag for free-form creative directives |
| FR-AI2 | Epic 21 | Router parses additional instructions into structured directive categories |
| FR-AI3 | Epic 21 | Router validates referenced media files exist and are accessible |
| FR-AI4 | Epic 21 | Router produces structured directive fields in router-output.json |
| FR-AI5 | Epic 21 | Content Creator consumes narrative overrides (tone, structure, pacing) |
| FR-AI6 | Epic 21 | FFmpeg Engineer applies user-specified transition effects |
| FR-AI7 | Epic 21 | FFmpeg Engineer inserts overlay images at specified moments |
| FR-AI8 | Epic 21 | Assembly incorporates user-provided documentary-style cutaway clips |

## Epic List

### Epic 18: Veo3 Production Hardening
Veo3 generation works reliably in automated pipeline runs. Duration constraints enforced (even-only: 4/6/8), rate limits handled with backoff, video download uses authenticated URI, auto-retry distinguishes transient from permanent failures.
**FRs covered:** FR60-FR64

### Epic 19: B-Roll Assembly Engine
Reel assembler produces correct full-opacity documentary cutaways using a proven two-pass approach (base reel + overlay pass). B-roll clips auto-upscaled to match segment dimensions. Timeline placement uses PTS-offset technique.
**FRs covered:** FR65-FR68

### Epic 20: Documentary Cutaway System
Pipeline can source external video clips (YouTube Shorts, user URLs) and auto-discover relevant reference content. Unified B-roll manifest merges Veo3 and external clips for assembly. Supports both user-directed and agent-suggested placements.
**FRs covered:** FR69-FR73

### Epic 21: Additional Creative Instructions
User can pass creative directives (images, videos, transitions, narrative changes) via the CLI. Includes full CLI refactoring to Command pattern (DI, interfaces, separation of concerns, command history). Router parses and structures directives. Downstream agents (Content Creator, FFmpeg Engineer, Assembly) consume them. No source file exceeds 500 lines.
**FRs covered:** FR-AI1 through FR-AI8

### Epic 1: Project Foundation & Pipeline Orchestration
Pedro has a running pipeline daemon with the complete skeleton: domain model, FSM, state persistence, agent execution, QA reflection loop, event logging, workspace isolation, and queue management. All Port Protocols defined, systemd service configured, Poetry project scaffolded.
**FRs covered:** FR20-FR24, FR35, FR38, FR39, FR40

### Epic 2: Telegram Trigger & Episode Analysis
Pedro can send a YouTube URL via Telegram, answer optional elicitation questions, and the pipeline downloads the episode, analyzes the full transcript, and selects the best 60-90 second moment based on context.
**FRs covered:** FR1-FR9

### Epic 3: Video Processing & Camera Intelligence
The pipeline detects camera layouts from extracted frames, applies per-segment crop strategies for vertical 9:16 video, handles layout transitions, and escalates unknown layouts to Pedro via Telegram for learning.
**FRs covered:** FR10-FR16

### Epic 4: Content Generation & Delivery
Pedro receives the finished Reel via Telegram with 3 description options, hashtags, and music suggestions. Videos over 50MB route to Google Drive. The full happy path (Journey 1) works end-to-end.
**FRs covered:** FR17-FR19, FR25-FR28

### Epic 5: Revision & Feedback Loop
Pedro can request targeted revisions via Telegram — extend moment, fix framing, different moment, add context. The Router Agent interprets feedback, routes to the right agent, and re-delivers only the changed output.
**FRs covered:** FR29-FR34

### Epic 6: Reliability, Recovery & Operations
Pipeline survives Pi crashes and auto-resumes from the last checkpoint. Resource monitoring defers processing when Pi is under stress. Auto-start on boot. Inspectable run history and knowledge base.
**FRs covered:** FR36, FR37, FR41, FR42, FR43

## Epic 1: Project Foundation & Pipeline Orchestration

Pedro has a running pipeline daemon with the complete skeleton: domain model, FSM, state persistence, agent execution, QA reflection loop, event logging, workspace isolation, and queue management. All Port Protocols defined, systemd service configured, Poetry project scaffolded.

### Story 1.1: Project Scaffolding & Domain Model

As a developer,
I want the project scaffolded with Poetry, Hexagonal Architecture, and all domain types defined,
So that I have a solid foundation with enforced layer boundaries to build pipeline components on.

**Acceptance Criteria:**

**Given** a fresh project directory
**When** I run `poetry install`
**Then** all dependencies are installed and the virtual environment is active
**And** pyproject.toml contains tool config for black, isort, ruff, mypy, pytest

**Given** the project structure exists
**When** I inspect `src/pipeline/domain/`
**Then** `types.py` defines NewType for RunId, AgentId, SessionId, GateName
**And** `enums.py` defines PipelineStage, QADecision, EscalationState, RevisionType
**And** `models.py` defines frozen dataclasses: AgentRequest, AgentResult, QACritique, CropRegion, VideoMetadata, QueueItem, RunState, PipelineEvent
**And** `errors.py` defines PipelineError hierarchy: ConfigurationError, ValidationError, AgentExecutionError, UnknownLayoutError
**And** `ports.py` defines 8 Port Protocols: AgentExecutionPort, ModelDispatchPort, MessagingPort, VideoProcessingPort, VideoDownloadPort, StateStorePort, FileDeliveryPort, KnowledgeBasePort
**And** `transitions.py` defines the FSM transition table and guard definitions as pure data

**Given** the domain layer
**When** I run `mypy --strict src/pipeline/domain/`
**Then** zero type errors and domain/ imports only from stdlib

### Story 1.2: Pipeline State Machine & File Persistence

As a developer,
I want a working FSM that tracks pipeline state and persists it to disk atomically,
So that the pipeline can track stage progression and survive restarts. (FR35, FR40)

**Acceptance Criteria:**

**Given** the PipelineStateMachine is initialized
**When** a valid transition is requested (e.g., ROUTER → RESEARCH after QA pass)
**Then** the state transitions and RunState reflects the new stage

**Given** an invalid transition is requested
**When** the FSM evaluates guards
**Then** the transition is rejected with a descriptive PipelineError

**Given** a state change occurs
**When** the FileStateStore persists RunState
**Then** `run.md` is written atomically (write-to-temp + rename)
**And** frontmatter matches the exact schema: run_id, youtube_url, current_stage, current_attempt, qa_status, stages_completed, escalation_state, best_of_three_overrides, created_at, updated_at

**Given** a persisted `run.md` exists
**When** FileStateStore loads it
**Then** RunState is correctly reconstructed from frontmatter

### Story 1.3: Agent Execution Engine

As a developer,
I want the orchestrator to execute BMAD agents via Claude Code CLI as subprocess calls,
So that pipeline stages can run AI agents and collect their output artifacts.

**Acceptance Criteria:**

**Given** a stage step file and agent definition
**When** the CliBackend executes `claude -p "{prompt}"`
**Then** the subprocess runs with the constructed prompt (step file + agent def + prior artifacts + elicitation context)
**And** execution is bounded by `asyncio.timeout()`

**Given** the agent process completes
**When** the orchestrator collects results
**Then** output artifacts are read from the per-run workspace directory
**And** an AgentResult is returned with status, artifacts, and session_id

**Given** the agent process fails or times out
**When** the executor detects the failure
**Then** an AgentExecutionError is raised with the cause preserved (`raise ... from exc`)

### Story 1.4: QA Reflection Loop

As a developer,
I want QA gates that validate stage outputs with prescriptive feedback and automatic rework,
So that quality is enforced autonomously with minimal human intervention. (FR20-FR24)

**Acceptance Criteria:**

**Given** an agent produces an artifact
**When** the ReflectionLoop evaluates it against gate criteria
**Then** a QACritique is returned matching the Pydantic-validated schema (decision, score, gate, attempt, blockers, prescriptive_fixes, confidence)

**Given** a QA gate returns REWORK with prescriptive feedback
**When** the reflection loop retries
**Then** the agent receives the exact fix instructions from the previous critique
**And** up to 3 attempts are made (hard cap)

**Given** 3 attempts all fail QA
**When** the best-of-three selector evaluates
**Then** the highest-scoring attempt is selected and the pipeline continues

**Given** all automated QA recovery is exhausted (score below minimum threshold)
**When** escalation is triggered
**Then** the user is notified via Telegram with QA feedback summary
**And** the pipeline pauses awaiting user guidance

### Story 1.5: Event Bus & Observability

As a developer,
I want an in-process event system that decouples state transitions from their side effects,
So that logging, checkpointing, and notifications happen automatically.

**Acceptance Criteria:**

**Given** the EventBus is initialized with listeners
**When** a PipelineEvent is published
**Then** all subscribed listeners receive the event
**And** listener failures do not block the publisher

**Given** a state transition event occurs
**When** the event_journal_writer receives it
**Then** an entry is appended to `events.log`: `<ISO8601> | <namespace.event_name> | <stage> | <json_data>`

**Given** a stage completion event occurs
**When** the frontmatter_checkpointer receives it
**Then** `run.md` is atomically updated with the latest RunState

**Given** a stage transition event occurs
**When** the telegram_notifier receives it
**Then** a status message is sent via Telegram: `"Processing stage {n}/{total}: {stage_name}..."`

### Story 1.6: Queue Management & Workspace Isolation

As a developer,
I want a FIFO queue for pipeline requests and isolated per-run workspaces,
So that concurrent requests are queued safely and each run's artifacts are contained. (FR38, FR39)

**Acceptance Criteria:**

**Given** a new pipeline request arrives
**When** the queue_consumer checks for work
**Then** the oldest item in `queue/inbox/` is claimed by moving to `queue/processing/`
**And** file locking (flock) prevents duplicate claims

**Given** a run is already in progress and a new URL is submitted
**When** the queue receives the request
**Then** it is queued in inbox/ with a timestamp-prefixed JSON file
**And** the user is notified of queue position via Telegram (FR4 support ready)

**Given** a run is claimed
**When** the workspace_manager creates a workspace
**Then** a new directory is created under `workspace/runs/<timestamp>-<short_id>/`
**And** all stage outputs are scoped to this workspace

**Given** a run completes
**When** the workspace context manager exits
**Then** the queue item moves from `processing/` to `completed/`

### Story 1.7: Recovery Chain & Error Handling

As a developer,
I want a multi-level error recovery chain,
So that transient failures are handled automatically before escalating to the user.

**Acceptance Criteria:**

**Given** an agent execution fails with a transient error
**When** the RecoveryChain processes it
**Then** Level 1 (retry) re-executes the same agent with the same session

**Given** a retry fails
**When** Level 2 (fork) is attempted
**Then** a new session is forked from the last checkpoint and the agent re-executes

**Given** a fork fails
**When** Level 3 (fresh) is attempted
**Then** a completely new session executes the agent from scratch

**Given** all automated recovery fails
**When** Level 6 (escalate) is triggered
**Then** the user is notified via Telegram with error context
**And** the pipeline pauses for user intervention

### Story 1.8: Composition Root & Service Bootstrap

As a developer,
I want the complete service wired together and running as a systemd daemon,
So that the pipeline starts on boot and is ready to process requests.

**Acceptance Criteria:**

**Given** the bootstrap module
**When** `create_orchestrator()` is called
**Then** all adapters are instantiated and wired to Port Protocols
**And** Pydantic BaseSettings loads config from `.env` + `config/*.yaml`
**And** EventBus is initialized with all listeners

**Given** systemd service is enabled
**When** the Pi boots
**Then** the service starts via `python3 -m pipeline.app.main`
**And** the daemon polls for queue items when idle

**Given** the BMAD workflow layer
**When** `workflow.md` is read
**Then** it defines pipeline stage sequence, agent resolution, and execution protocol
**And** `qa-gate-template.md` defines shared QA execution rules and prescriptive feedback protocol

## Epic 2: Telegram Trigger & Episode Analysis

Pedro can send a YouTube URL via Telegram, answer optional elicitation questions, and the pipeline downloads the episode, analyzes the full transcript, and selects the best 60-90 second moment based on context.

### Story 2.1: Telegram Bot Polling & URL Validation

As a user,
I want to send a YouTube URL via Telegram and have it queued for processing,
So that I can trigger the pipeline from my phone with zero friction. (FR1)

**Acceptance Criteria:**

**Given** the pipeline daemon is running
**When** Pedro sends a YouTube URL to the Telegram bot
**Then** the URL is validated as a YouTube link
**And** a queue item is created in `queue/inbox/` with the URL and Telegram update_id

**Given** a non-YouTube URL is sent
**When** the URL validator checks it
**Then** the message is rejected with a friendly Telegram reply: "Please send a YouTube URL"

**Given** a duplicate URL (same update_id) arrives
**When** the polling listener processes it
**Then** the duplicate is silently ignored

**Given** a message from an unauthorized CHAT_ID
**When** the polling listener receives it
**Then** the message is logged and silently ignored (NFR-S2)

### Story 2.2: Router Agent — Elicitation & Smart Defaults

As a user,
I want the pipeline to ask me quick clarifying questions or proceed with smart defaults,
So that I can give direction when I want to or just send a URL and go. (FR2, FR3, FR4)

**Acceptance Criteria:**

**Given** a new run starts
**When** the Router Agent executes stage-01-router.md
**Then** it parses the YouTube URL and retrieves basic metadata
**And** asks 0-2 elicitation questions via Telegram `ask_user` (topic focus, duration preference)

**Given** the user provides topic focus (e.g., "CAP theorem debate")
**When** the Router Agent processes the response
**Then** the elicitation context is saved to the workspace for downstream agents

**Given** the user provides only a URL with no additional context
**When** the Router Agent applies smart defaults
**Then** predefined defaults from pipeline configuration are used
**And** the pipeline proceeds without further questions

**Given** a run is already in progress when a new URL arrives
**When** the queue consumer detects the active run
**Then** the user is notified of queue position via Telegram (FR4)

**BMAD artifacts:** `stage-01-router.md`, `agents/router/agent.md`, `agents/router/elicitation-flow.md`, `qa/gate-criteria/router-criteria.md`

### Story 2.3: Research Agent — Episode Metadata & Context

As a user,
I want the pipeline to research the full episode context before selecting moments,
So that moment selection is informed by topic, narrative structure, and episode context. (FR5)

**Acceptance Criteria:**

**Given** the Router stage completed with elicitation context
**When** the Research Agent executes stage-02-research.md
**Then** video metadata is extracted via yt-dlp: title, duration, channel, publish date, description
**And** the metadata is saved as a structured artifact in the workspace

**Given** yt-dlp metadata extraction fails
**When** the retry logic executes
**Then** up to 3 retries with exponential backoff are attempted (NFR-I3)
**And** failure after retries raises an error handled by the recovery chain

**Given** research artifacts are produced
**When** the QA gate evaluates against research-criteria.md
**Then** the critique validates completeness of metadata and context summary

**BMAD artifacts:** `stage-02-research.md`, `agents/research/agent.md`, `agents/research/metadata-extraction.md`, `qa/gate-criteria/research-criteria.md`

### Story 2.4: Transcript Agent — Moment Selection

As a user,
I want the pipeline to analyze the full transcript and select the most compelling 60-90 second moment,
So that the Reel captures the best part of the episode. (FR6, FR7, FR8, FR9)

**Acceptance Criteria:**

**Given** research artifacts and elicitation context are available
**When** the Transcript Agent executes stage-03-transcript.md
**Then** episode subtitles/transcripts are downloaded via yt-dlp
**And** the full transcript is analyzed for narrative structure, emotional peaks, and quotable statement density

**Given** the user specified a topic focus
**When** moment selection runs
**Then** scoring is weighted toward segments matching the specified topic (FR8)

**Given** the transcript analysis is complete
**When** the agent selects a segment
**Then** a 60-90 second segment is chosen with precise start/end timestamps (FR9)
**And** the selection rationale is documented in the output artifact

**Given** the moment selection artifact is produced
**When** the QA gate evaluates against transcript-criteria.md
**Then** the critique validates segment length, timestamp precision, and selection rationale quality

**BMAD artifacts:** `stage-03-transcript.md`, `agents/transcript/agent.md`, `agents/transcript/moment-selection-criteria.md`, `qa/gate-criteria/transcript-criteria.md`

## Epic 3: Video Processing & Camera Intelligence

The pipeline detects camera layouts from extracted frames, applies per-segment crop strategies for vertical 9:16 video, handles layout transitions, and escalates unknown layouts to Pedro via Telegram for learning.

### Story 3.1: Layout Detective — Frame Extraction & Classification

As a user,
I want the pipeline to automatically detect camera layouts in each segment,
So that the correct crop strategy is applied without manual inspection. (FR10, FR11)

**Acceptance Criteria:**

**Given** a selected moment with start/end timestamps
**When** the Layout Detective executes stage-05-layout-detective.md
**Then** key frames are extracted from the source video at configurable intervals via FFmpeg (FR10)
**And** each frame is classified as side-by-side, speaker-focus, grid, or unknown (FR11)

**Given** a segment contains multiple layout types
**When** the agent analyzes frame sequences
**Then** layout transition boundaries are identified with frame-level timestamps

**Given** the classification artifacts are produced
**When** the QA gate evaluates against layout-criteria.md
**Then** the critique validates that all segments have a layout classification and that known layouts have matching crop strategies

**BMAD artifacts:** `stage-05-layout-detective.md`, `agents/layout-detective/agent.md`, `agents/layout-detective/frame-analysis.md`, `qa/gate-criteria/layout-criteria.md`

### Story 3.2: FFmpeg Engineer — Crop & Encode

As a user,
I want the pipeline to produce a vertical 9:16 video with intelligent per-segment framing,
So that each speaker is properly framed in the final Reel. (FR12, FR13)

**Acceptance Criteria:**

**Given** classified layout segments with crop strategies
**When** the FFmpeg Engineer executes stage-06-ffmpeg-engineer.md
**Then** per-segment crop regions are applied to produce vertical 9:16 video at 1080x1920 (FR12)
**And** FFmpeg runs with `-threads 2` and respects memory/CPU constraints (NFR-P4, NFR-P5)

**Given** a segment contains a layout transition
**When** the encoder processes it
**Then** the segment is split at frame boundaries and each sub-segment gets its own crop strategy (FR13)

**Given** the encoded video is produced
**When** the QA gate evaluates against ffmpeg-criteria.md
**Then** the critique validates resolution, aspect ratio, crop accuracy, and encoding quality

**Given** video intermediates are being processed
**When** FFmpeg writes temporary files
**Then** tmpfs is used where possible to reduce SD card wear (NFR-P6)

**BMAD artifacts:** `stage-06-ffmpeg-engineer.md`, `agents/ffmpeg-engineer/agent.md`, `agents/ffmpeg-engineer/crop-playbook.md`, `agents/ffmpeg-engineer/encoding-params.md`, `qa/gate-criteria/ffmpeg-criteria.md`

### Story 3.3: Unknown Layout Escalation & Learning

As a user,
I want to be asked for help when the pipeline encounters an unknown camera layout, and have it learn from my answer,
So that the system gets smarter with every run. (FR14, FR15, FR16)

**Acceptance Criteria:**

**Given** the Layout Detective encounters a layout that doesn't match any known strategy
**When** escalation is triggered
**Then** a screenshot of the unknown frame is sent to Pedro via Telegram with options: "(A) Focus speaker left, (B) Focus speaker right, (C) Custom guidance" (FR14)

**Given** Pedro replies with layout guidance
**When** the system processes the response
**Then** the guidance is stored as a new crop strategy in `config/crop-strategies.yaml` (FR15)
**And** the pipeline resumes with the new strategy applied

**Given** a previously-learned layout appears in a future run
**When** the Layout Detective classifies it
**Then** the layout is automatically recognized and the stored crop strategy is applied without escalation (FR16)

**BMAD artifacts:** `agents/layout-detective/escalation-protocol.md`
**Python:** `knowledge_base_adapter.py` (YamlKnowledgeBase — crop-strategies.yaml CRUD)

### Story 3.4: Final Reel Assembly

As a user,
I want the encoded segments assembled into a single polished Reel,
So that the output is a complete, publish-ready video file.

**Acceptance Criteria:**

**Given** all segments are encoded with correct crop strategies
**When** the Assembly stage executes stage-07-assembly.md
**Then** segments are concatenated into a single video file
**And** transitions between segments are handled cleanly

**Given** the assembled Reel is produced
**When** the QA gate evaluates against assembly-criteria.md
**Then** the critique validates total duration (60-90s target), visual continuity, and output format compliance

**BMAD artifacts:** `stage-07-assembly.md`, `qa/gate-criteria/assembly-criteria.md`

## Epic 4: Content Generation & Delivery

Pedro receives the finished Reel via Telegram with 3 description options, hashtags, and music suggestions. Videos over 50MB route to Google Drive. The full happy path (Journey 1) works end-to-end.

### Story 4.1: Content Creator Agent — Descriptions, Hashtags & Music

As a user,
I want AI-generated Instagram descriptions, hashtags, and music suggestions alongside my Reel,
So that I can post quickly with minimal content creation effort. (FR17, FR18, FR19)

**Acceptance Criteria:**

**Given** a selected moment with context from research and transcript analysis
**When** the Content Creator executes stage-04-content.md
**Then** 3 Instagram description options are generated, relevant to the selected moment (FR17)
**And** relevant hashtags are generated (FR18)
**And** a background music suggestion is provided matching the detected content mood category (FR19)

**Given** the content artifacts are produced
**When** the QA gate evaluates against content-criteria.md
**Then** the critique validates description relevance, hashtag appropriateness, and mood-music alignment

**BMAD artifacts:** `stage-04-content.md`, `agents/content-creator/agent.md`, `agents/content-creator/description-style-guide.md`, `agents/content-creator/hashtag-strategy.md`, `qa/gate-criteria/content-criteria.md`

### Story 4.2: Delivery Agent — Telegram Video & Content Options

As a user,
I want to receive the finished Reel and content options as a structured Telegram message sequence,
So that I can review everything in one place and decide what to post. (FR25, FR26)

**Acceptance Criteria:**

**Given** the Reel and content artifacts are ready
**When** the Delivery Agent executes stage-08-delivery.md
**Then** the video is delivered first via Telegram `send_file` (FR25)
**And** description options, hashtags, and music suggestions follow as structured messages (FR26)

**Given** the delivery sequence completes
**When** Pedro receives the messages
**Then** the message format follows the defined template: video → descriptions → hashtags + music

**BMAD artifacts:** `stage-08-delivery.md`, `agents/delivery/agent.md`, `agents/delivery/message-templates.md`

### Story 4.3: Google Drive Fallback for Large Files

As a user,
I want videos over 50MB to be uploaded to Google Drive with a link delivered via Telegram,
So that large Reels still reach me without hitting Telegram's file size limit. (FR27)

**Acceptance Criteria:**

**Given** a finished Reel exceeds 50MB
**When** the delivery stage checks file size
**Then** the video is uploaded to Google Drive via the GoogleDriveUploader adapter
**And** a shareable link is delivered via Telegram instead of the file

**Given** a Reel is under 50MB
**When** the delivery stage checks file size
**Then** the video is sent inline via Telegram as usual

**Python:** `google_drive_adapter.py` (GoogleDriveUploader — OAuth2 service account)

### Story 4.4: End-to-End Happy Path Integration

As a user,
I want to send a URL and receive a complete, publish-ready Reel with content options,
So that the full Journey 1 (Happy Path) works autonomously. (FR28)

**Acceptance Criteria:**

**Given** the complete pipeline is wired (all 8 stages)
**When** Pedro sends a YouTube URL via Telegram
**Then** the pipeline runs all stages: Router → Research → Transcript → Content → Layout Detective → FFmpeg Engineer → Assembly → Delivery
**And** QA gates validate each stage output
**And** Pedro receives video + content options in Telegram

**Given** Pedro reviews the delivered Reel
**When** he is satisfied with the result
**Then** he can approve and proceed to publish (FR28)

**Given** the end-to-end run completes
**When** the run history is inspected
**Then** `run.md` shows all stages completed, `events.log` shows the full execution timeline

## Epic 5: Revision & Feedback Loop

Pedro can request targeted revisions via Telegram — extend moment, fix framing, different moment, add context. The Router Agent interprets feedback, routes to the right agent, and re-delivers only the changed output.

### Story 5.1: Revision Type Detection & Routing

As a user,
I want the pipeline to understand my revision requests and route them to the right agent,
So that I don't have to re-run the full pipeline for minor fixes. (FR33)

**Acceptance Criteria:**

**Given** Pedro sends a revision message after receiving a Reel
**When** the Router Agent interprets the feedback
**Then** the revision type is classified as one of: extend_moment, fix_framing, different_moment, add_context
**And** the request is routed to the appropriate agent without re-running the full pipeline

**Given** an ambiguous revision message
**When** the Router can't confidently classify it
**Then** it asks Pedro a clarifying question via Telegram

**BMAD artifacts:** `agents/router/revision-interpretation.md`
**Python:** `revision_router.py`

### Story 5.2: Extend Moment Revision

As a user,
I want to include more seconds before or after the selected clip,
So that the Reel captures the full context of the moment. (FR29)

**Acceptance Criteria:**

**Given** Pedro replies "Include 15 more seconds before the cut"
**When** the revision is routed to the Transcript Agent
**Then** timestamps are adjusted to widen the window by the requested amount
**And** FFmpeg re-encodes the extended segment with the same crop strategy
**And** QA validates the revised output
**And** only the changed Reel is re-delivered

**BMAD artifacts:** `revision-flows/revision-extend-moment.md`

### Story 5.3: Fix Framing Revision

As a user,
I want to correct the camera framing on a specific segment,
So that the right speaker is in frame. (FR30)

**Acceptance Criteria:**

**Given** Pedro replies "Segment 2 framing is wrong — focus on the right speaker"
**When** the revision is routed to the FFmpeg Engineer
**Then** only the affected segment is re-processed with the corrected crop instruction
**And** the segment is re-assembled into the final Reel
**And** QA validates the revised output

**BMAD artifacts:** `revision-flows/revision-fix-framing.md`

### Story 5.4: Different Moment Revision

As a user,
I want to request a completely different moment from the episode,
So that I can explore alternative clips. (FR31)

**Acceptance Criteria:**

**Given** Pedro replies "Try a different moment — around 45:00 where we discuss event sourcing"
**When** the revision is routed to the Transcript Agent
**Then** moment selection re-runs targeting the specified area
**And** the full downstream pipeline re-processes (Layout → FFmpeg → Assembly → Delivery)
**And** QA validates at each gate

**BMAD artifacts:** `revision-flows/revision-different-moment.md`

### Story 5.5: Add Context Revision & Incremental Re-Delivery

As a user,
I want to expand the clip with wider context and receive only the changed output,
So that the Reel has proper setup without re-reviewing unchanged content. (FR32, FR34)

**Acceptance Criteria:**

**Given** Pedro replies "Include the setup where we explain the problem"
**When** the revision is routed to the Transcript Agent
**Then** the timestamp window is widened to include surrounding context
**And** the pipeline re-processes from the adjusted timestamps

**Given** a revision produces a new Reel
**When** re-delivery occurs
**Then** only the changed output is delivered (incremental re-delivery) (FR34)
**And** Pedro does not re-receive unchanged content options

**BMAD artifacts:** `revision-flows/revision-add-context.md`

## Epic 6: Reliability, Recovery & Operations

Pipeline survives Pi crashes and auto-resumes from the last checkpoint. Resource monitoring defers processing when Pi is under stress. Auto-start on boot. Inspectable run history and knowledge base.

### Story 6.1: Crash Detection & Checkpoint Resume

As a user,
I want the pipeline to resume from the last checkpoint after a crash,
So that I don't lose 20+ minutes of completed work. (FR36, FR37)

**Acceptance Criteria:**

**Given** the Pi reboots after a power interruption
**When** the pipeline service starts
**Then** it checks for in-progress runs by scanning `workspace/runs/` for incomplete `run.md` files
**And** resumes from the last completed checkpoint stage (FR36)
**And** resumes within 60 seconds of restart (NFR-R2)

**Given** an interrupted run is detected
**When** the pipeline resumes
**Then** Pedro is notified via Telegram: "Resuming your run from {stage_name} ({n} of {total} stages already completed)" (FR37)

### Story 6.2: systemd Auto-Start & Watchdog

As a user,
I want the pipeline to start automatically on boot and restart after crashes,
So that the service is always available without manual intervention. (FR41)

**Acceptance Criteria:**

**Given** the systemd service is installed and enabled
**When** the Pi boots
**Then** the pipeline service starts automatically

**Given** the pipeline process crashes
**When** systemd detects the exit
**Then** the service restarts within 30 seconds (RestartSec=30, NFR-R4)

**Given** the pipeline is actively processing
**When** the watchdog timer runs
**Then** the pipeline sends heartbeats every ≤5 minutes (WatchdogSec=300, NFR-R5)
**And** a stale process is auto-killed and restarted

### Story 6.3: Resource Monitoring & Throttling

As a user,
I want the pipeline to check system resources before heavy processing,
So that Umbrel services aren't disrupted by pipeline runs. (FR42)

**Acceptance Criteria:**

**Given** an FFmpeg encoding stage is about to start
**When** the resource_monitor checks system state
**Then** memory usage, CPU load, and thermal state are evaluated
**And** processing is deferred if memory > 3GB or CPU > 80% or temperature is critical (NFR-P4, NFR-P5)

**Given** resources are constrained
**When** the monitor defers processing
**Then** Pedro is notified via Telegram: "Pipeline paused — Pi is under load. Resuming automatically..."
**And** the monitor retries at configurable intervals until resources are available

### Story 6.4: Operations Tooling & Filesystem Inspection

As a user,
I want to inspect run history, QA feedback, and the knowledge base through the filesystem,
So that I can understand what the pipeline is doing and make targeted improvements. (FR43)

**Acceptance Criteria:**

**Given** completed pipeline runs exist
**When** Pedro browses `workspace/runs/`
**Then** each run directory contains human-readable `run.md` (frontmatter state), `events.log` (timeline), and all artifacts

**Given** the knowledge base exists
**When** Pedro opens `config/crop-strategies.yaml`
**Then** all learned layouts are listed with human-readable descriptions and crop parameters

**Given** old run assets accumulate
**When** the cleanup script runs
**Then** run assets older than 30 days are deleted, keeping only final Reels and `run.md` metadata

## Epic 15: Boundary Frame Guard

The FFmpeg Engineer agent validates face count at segment boundaries before encoding and trims misaligned boundaries to prevent wrong-crop artifacts at camera transitions. The QA gates detect surviving misalignment and issue prescriptive fixes. Two-layer defense: Prevention (Story 15-1) + Detection (Story 15-2).

### Story 15.1: FFmpeg Engineer — Boundary Frame Guard Prevention

As a pipeline user,
I want the FFmpeg Engineer to verify face count at segment boundaries and trim misaligned boundaries before encoding,
so that camera transition frames are never encoded with the wrong crop filter.

**Files affected:** `crop-failure-modes.md` (FM-4), `crop-playbook.md` (Boundary Frame Guard section), `agent.md` (boundary_validation field), `stage-06-ffmpeg-engineer.md` (step 7 + step 11 amendment)

### Story 15.2: QA Gate — Boundary Frame Alignment Detection

As a pipeline user,
I want the QA gates to detect wrong-crop-at-boundary artifacts and issue prescriptive fixes,
so that misaligned boundaries are caught even when the FFmpeg Engineer's prevention layer misses them.

**Files affected:** `ffmpeg-criteria.md` (Dimension 8 + weight redistribution), `assembly-criteria.md` (Dim 3 trim exemption + Dim 5 framing mismatch), `stage-07-assembly.md` (trim-aware duration step)

## Epic 16: Multi-Moment Narrative Selection

Pedro can request shorts with 2-5 complementary transcript moments that build a narrative arc. Triggered automatically when `--target-duration > 120` or explicitly via `--moments N`. Builds on Epic 14 infrastructure (`NarrativeMoment` dataclass, `NarrativeRole` enum, `TransitionKind.NARRATIVE_BOUNDARY`, `--target-duration` CLI flag, xfade assembly support).

### Story 16.1: NarrativePlan Domain Model & Parser

As a pipeline developer,
I want a `NarrativePlan` domain model and a parser that extracts multi-moment structures from agent JSON output,
so that the pipeline can represent and deserialize narrative arcs with graceful fallback to single-moment on parse failure.

**Files affected:** `domain/models.py` (NarrativePlan dataclass), `application/moment_parser.py` (parser + fallback), tests

### Story 16.2: CLI --moments Flag & Auto-Trigger

As a pipeline user,
I want a `--moments N` CLI flag that explicitly requests multi-moment selection, and automatic multi-moment activation when `--target-duration > 120`,
so that I can control narrative complexity directly or let the pipeline decide based on duration.

**Files affected:** `scripts/run_cli.py` (CLI flag), `application/orchestrator.py` (auto-trigger logic), `CLAUDE.md` (docs update), tests

### Story 16.3: Transcript Agent Multi-Moment Selection

As a pipeline user,
I want the transcript agent to select 2-5 complementary moments with narrative roles when multi-moment mode is active,
so that extended shorts follow a coherent narrative arc instead of one long continuous block.

**Files affected:** `agents/transcript/agent.md` (prompt), `agents/transcript/moment-selection-criteria.md` (multi-moment criteria), `qa/gate-criteria/transcript-criteria.md` (QA dimensions), `workflows/stages/stage-03-transcript.md` (multi-moment step)

### Story 16.4: Downstream Stage Multi-Moment Support

As a pipeline user,
I want stages 5-7 (Layout Detective, FFmpeg Engineer, Assembly) to process multiple moments with chronological I/O ordering for Pi performance,
so that the full pipeline produces a coherent multi-moment Reel end-to-end.

**Files affected:** `workflows/stages/stage-05-layout-detective.md` (multi-moment loop), `workflows/stages/stage-06-ffmpeg-engineer.md` (per-moment encoding), `workflows/stages/stage-07-assembly.md` (narrative-ordered assembly), `qa/gate-criteria/assembly-criteria.md` (multi-moment validation)

## Epic 17: Veo3 Animated B-Roll Integration

Pedro can enrich Reels with AI-generated animated B-roll clips produced by Gemini Veo3. The Content Creator agent directs clip placement using narrative anchors (story language, not timestamps). Async generation runs parallel to Stages 5-6, a formal `VEO3_AWAIT` pipeline stage blocks before Assembly, and Assembly weaves clips into the final reel as documentary-style cutaways (silent video over continuous speaker audio). Builds on Epic 11 infrastructure (`Veo3Prompt` dataclass, `publishing-assets.json` with `veo3_prompts[]`).

**Brainstorming source:** `_bmad-output/brainstorming/brainstorming-session-2026-02-23.md` (29 ideas, 3 decision trees, consensus-validated architecture)

**Implementation order:** 17.1 → 17.2 → 17.3 → 17.4 → 17.5 → 17.6 → 17.7 → 17.8 (17.5 parallel with 17.4)

### Story 17.1: Veo3 Domain Models

As a pipeline developer,
I want to extend the existing `Veo3Prompt` frozen dataclass and add new `Veo3Job` and `Veo3JobStatus` models,
so that the domain layer can represent Veo3 generation state and editorial intent without external dependencies.

**Acceptance criteria:**
- Extend existing `Veo3Prompt(variant, prompt)` in `domain/models.py` with three new fields: `narrative_anchor: str`, `duration_s: int`, `idempotent_key: str` (preserving frozen + tuple conventions)
- New `Veo3JobStatus` enum: `pending`, `generating`, `completed`, `failed`, `timed_out`
- New `Veo3Job` frozen dataclass: `idempotent_key`, `variant`, `prompt`, `status`, `video_path`, `error_message`
- Variant taxonomy: `intro`, `broll`, `outro`, `transition` as string constants
- Idempotent key pattern: `{run_id}_{variant}` — deterministic, zero collision risk
- All models use stdlib only (frozen dataclass, tuple, Mapping) — no Pydantic in domain
- Existing `PublishingAssets.veo3_prompts` tuple type remains compatible with extended Veo3Prompt
- Unit tests for dataclass construction, immutability, and idempotent key generation

**Files affected:** `domain/models.py` (extend existing Veo3Prompt, new Veo3Job, Veo3JobStatus), tests

### Story 17.2: VideoGenerationPort Protocol

As a pipeline developer,
I want a `VideoGenerationPort` protocol defining the contract for async video generation services,
so that the domain and application layers depend on an abstraction, not on Gemini-specific implementation details.

**Acceptance criteria:**
- `VideoGenerationPort` added as 11th port protocol (after existing 10: AgentExecution, ModelDispatch, Messaging, Queue, VideoProcessing, VideoDownload, StateStore, FileDelivery, KnowledgeBase, ResourceMonitor)
- Methods: `submit_job(prompt: Veo3Prompt) -> Veo3Job`, `poll_job(idempotent_key: str) -> Veo3Job`, `download_clip(job: Veo3Job, dest: Path) -> Path`
- Protocol follows existing port conventions (runtime_checkable, docstrings, async methods)
- Application layer imports port via `TYPE_CHECKING` guard
- Port documented in architecture decisions
- Unit tests for protocol structural subtyping

**Files affected:** `domain/ports.py` (VideoGenerationPort), tests

### Story 17.3: Gemini Veo3 Adapter & Settings

As a pipeline developer,
I want a `GeminiVeo3Adapter` that implements `VideoGenerationPort` using the Gemini API, with all Veo3 configuration centralized in PipelineSettings,
so that the pipeline can generate Veo3 video clips through a swappable infrastructure adapter with environment-driven configuration.

**Acceptance criteria:**
- `GeminiVeo3Adapter` in infrastructure layer implements all `VideoGenerationPort` methods
- Uses `google-genai` SDK with Gemini API for Veo3 model
- Requests 9:16 vertical format, silent audio, duration from prompt's `duration_s`
- Sends idempotent key with each API call for deduplication
- Handles API errors with proper exception chaining (`raise X from Y`)
- All Veo3 settings consolidated in `app/settings.py` (single owner): `GEMINI_API_KEY`, `VEO3_CLIP_COUNT` (default 3), `VEO3_TIMEOUT_S` (default 300), `VEO3_CROP_BOTTOM_PX` (default 16)
- Fake adapter for testing (returns canned responses)
- `.env.example` updated with all Veo3 env vars documented

**Files affected:** `infrastructure/adapters/gemini_veo3_adapter.py` (new), `app/settings.py` (all Veo3 config), `.env.example`, tests

### Story 17.4: Async Generation Orchestration & Polling Worker

As a pipeline developer,
I want an orchestration service that fires parallel Veo3 API calls after Stage 4 and a polling worker that tracks job status with adaptive backoff,
so that video generation runs concurrently with Stages 5-6 and job state is reliably tracked.

**Acceptance criteria:**
- After Stage 4 (CONTENT), reads `veo3_prompts[]` from `publishing-assets.json`
- Caps requests at `VEO3_CLIP_COUNT` from settings
- Fires parallel async `submit_job()` calls via `VideoGenerationPort`
- Creates `veo3/` subfolder in run directory
- Writes `veo3/jobs.json` with per-clip status using atomic writes (write-to-tmp + rename)
- Polling worker: adaptive backoff (fast when status changes, patient when idle)
- Per-clip independent tracking — partial success beats all-or-nothing
- Idempotent keys from `{run_id}_{variant}` pattern
- `pipeline_runner.py` modified to fire async generation after CONTENT stage completes (non-blocking, runs alongside Stages 5-6)
- Integration tests with fake adapter

**Files affected:** `application/veo3_orchestrator.py` (new), `application/pipeline_runner.py` (post-Stage-4 async hook), `infrastructure/adapters/` (jobs.json I/O), tests

### Story 17.5: Content Creator Agent Veo3 Direction

As a pipeline user,
I want the Content Creator agent to produce enriched `veo3_prompts` with narrative anchors, duration, and visual style direction,
so that the editorial director specifies clip placement and aesthetics in story language.

**Acceptance criteria:**
- Content Creator agent prompt updated to generate enriched veo3_prompts
- Each prompt includes: `variant` (intro/broll/outro/transition), `prompt` (visual description with style direction), `narrative_anchor` (story language reference to content moment), `duration_s` (5-8s, director's choice)
- Variant types serve as classification taxonomy with implicit placement semantics
- Visual style in prompts matches reel's overall aesthetic (director-specified)
- Clip count is director's choice, capped by `VEO3_CLIP_COUNT`
- QA gate validates enriched prompt structure
- Updated `publishing-assets.json` schema with enriched prompts

**Files affected:** `agents/content-creator/agent.md` (prompt update), `qa/gate-criteria/content-criteria.md` (enriched prompt validation), `domain/models.py` (if schema adjustment needed), tests

### Story 17.6: Veo3 Clip Post-Processing & Quality Validation

As a pipeline developer,
I want downloaded Veo3 clips to be automatically cropped (watermark removal) and quality-validated before the await gate passes them to Assembly,
so that only clips meeting resolution, duration, and visual quality standards enter the final reel.

**Acceptance criteria:**
- Always-crop strategy: unconditional FFmpeg bottom strip crop (`crop=in_w:in_h-{px}:0:0`) on every downloaded clip
- Crop pixels from `VEO3_CROP_BOTTOM_PX` setting (defined in Story 17.3)
- Quality validation checks: resolution matches 9:16, duration within ±1s of requested, no black-frame sequences
- Failed validation marks clip as `failed` in `jobs.json` — Assembly skips it
- Exposes `crop_and_validate(clip_path: Path, expected_duration_s: int) -> bool` for await gate to call
- Unit tests for crop filter construction + validation logic

**Files affected:** `infrastructure/adapters/veo3_postprocessor.py` (new), tests

### Story 17.7: Await Gate Pipeline Stage

As a pipeline developer,
I want a formal `VEO3_AWAIT` pipeline stage that blocks before Assembly until all Veo3 jobs resolve or timeout,
so that the await is checkpoint-recoverable and Assembly has access to all available generated clips.

**Acceptance criteria:**
- `PipelineStage.VEO3_AWAIT` added to stage enum, inserted into `_STAGE_SEQUENCE` between FFMPEG_ENGINEER and ASSEMBLY
- FSM transitions updated in `domain/transitions.py`: `(FFMPEG_ENGINEER, qa_pass) → VEO3_AWAIT`, `(VEO3_AWAIT, stage_complete) → ASSEMBLY`
- `pipeline_runner.py` handles VEO3_AWAIT as a non-agent stage (no QA gate) — executes await gate logic directly
- Reads `veo3/jobs.json` to check resolution status
- Polls with exponential backoff until all jobs resolved or `VEO3_TIMEOUT_S` exceeded
- Downloads completed clips to `veo3/` subfolder, applies crop + validation via Story 17.6's `crop_and_validate()`
- Evaluates: all completed → proceed, some failed → proceed with available, all failed → proceed without B-roll (emergency fallback)
- Updates `veo3/jobs.json` with final status after gate
- State checkpointed before and after gate — crash during 300s wait recovers by re-checking `veo3/jobs.json` on resume
- Emits EventBus events: `veo3.gate.started`, `veo3.gate.completed`, `veo3.gate.timeout`
- Integration tests for all three evaluation paths + crash recovery

**Files affected:** `domain/transitions.py` (VEO3_AWAIT state + transitions), `application/pipeline_runner.py` (stage sequence + gate handler), `application/veo3_await_gate.py` (new), tests

### Story 17.8: Assembly Stage B-Roll Insertion

As a pipeline user,
I want the Assembly stage to weave Veo3 B-roll clips into the final reel using variant-driven placement and documentary cutaway audio model,
so that the finished short includes animated visuals that enhance the narrative without disrupting speaker audio.

**Acceptance criteria:**
- Assembly reads `veo3/` folder for available clips + `content.json` for narrative anchors
- Variant-driven placement: `intro` → start, `outro` → end, `transition` → between moments, `broll` → narrative anchor match
- Narrative anchor matching: semantic/fuzzy match against content.json and transcript (not exact string match)
- Skip fallback: unmatched anchors skip gracefully (no crash, log warning)
- B-roll clips spliced into the segment list *before* FFmpeg filter graph construction — not inserted mid-chain
- New `_build_cutaway_filter()` method in `reel_assembler.py` for documentary cutaway: maps Veo3 video stream over the base segment's audio stream (independent video/audio stream mapping via FFmpeg overlay + stream selection)
- Existing `_build_xfade_filter()` remains unchanged — cutaway is a separate filter path
- Director-specified duration (5-8s) honored for each clip
- Reuses existing xfade transitions: 0.5s style-change fade for B-roll entry/exit points
- Assembly proceeds normally if no clips available (graceful degradation)
- Assembly report includes B-roll insertion details (which clips used, placement, any skipped)
- Integration tests for all placement variants + cutaway audio continuity + no-clip fallback

**Files affected:** `infrastructure/adapters/reel_assembler.py` (new `_build_cutaway_filter()` method + B-roll segment splicing), `workflows/stages/stage-07-assembly.md` (B-roll step), `qa/gate-criteria/assembly-criteria.md` (B-roll validation dimension), tests

## Epic 18: Veo3 Production Hardening

Veo3 generation works reliably in automated pipeline runs. Every bug discovered during the first production run is fixed: duration constraints, rate limits, video download authentication, auto-retry logic, and timeout wiring. No new features — just make the existing Veo3 integration production-grade.

**Production findings source:** First end-to-end run on 2026-02-25, workspace `20260225-131343-911335`

**Implementation order:** 18.1 → 18.2 → 18.3 → 18.4 → 18.5 (18.1-18.3 can be parallelized)

### Story 18.1: Fix Veo3 Duration Constraints

As a pipeline developer,
I want the adapter to enforce Veo3 API duration constraints (even-only values: 4, 6, 8),
so that generation requests never fail with `INVALID_ARGUMENT` for out-of-bound durations.

**Acceptance criteria:**
- `GeminiVeo3Adapter.submit_job()` clamps `prompt.duration_s` to nearest valid even value: odd values round up (5→6, 7→8), values below 4 become 4, values above 8 become 8
- `duration_seconds` parameter passed as `int`, not `str` (API accepts both but int is canonical)
- Domain model `Veo3Prompt.duration_s` validation relaxed: accept 0 (auto) or 4-8 (was 5-8)
- When `duration_s` is 0 (unset), adapter defaults to 6 (middle value)
- `_convert_prompts()` in orchestrator passes through raw duration — clamping happens in adapter (single responsibility)
- Unit tests for all clamping edge cases: 0→6, 3→4, 5→6, 7→8, 9→8

**Files affected:** `infrastructure/adapters/gemini_veo3_adapter.py` (clamp logic), `domain/models.py` (relax validation), tests

### Story 18.2: Authenticated Video Download

As a pipeline developer,
I want completed Veo3 clips to be downloaded via the Gemini Files API with proper authentication,
so that the await gate can retrieve generated videos instead of failing with "Saving remote videos is not supported".

**Acceptance criteria:**
- `GeminiVeo3Adapter.download_clip()` fully implemented (currently stub)
- Uses `operations.get()` with `GenerateVideosOperation(name=op_name)` to poll completed operations
- Extracts `video.uri` from `op.result.generated_videos[0].video`
- Downloads via SDK `httpx` client with API key header (not `?key=` query parameter — avoids credential leak in logs/referer)
- Writes video to `veo3/{variant}.mp4` in workspace
- `Veo3Job` domain model extended with `operation_name: str` field for resume/re-download capability
- `Veo3GenerationPort` protocol updated: `submit_job()` returns operation name alongside job status
- Adapter stores operation references (dict keyed by idempotent_key) for polling without re-submission
- Handles download failure gracefully: marks job as `failed` with `error_message="download_failed"`
- Integration test with fake HTTP server or mock

**Files affected:** `infrastructure/adapters/gemini_veo3_adapter.py` (download_clip, operation storage), `domain/models.py` (Veo3Job.operation_name), `domain/ports.py` (Veo3GenerationPort return type), `application/veo3_orchestrator.py` (pass operation refs), `application/veo3_await_gate.py` (call download), tests

### Story 18.3: Rate Limit Handling & Sequential Submission

As a pipeline developer,
I want Veo3 job submission to handle 429 RESOURCE_EXHAUSTED errors with exponential backoff and sequential submission with delays,
so that the pipeline doesn't exhaust API quota by firing all jobs simultaneously.

**Acceptance criteria:**
- `Veo3Orchestrator._submit_all()` changed from `asyncio.gather()` (parallel) to sequential with 5s delay between submissions
- On 429 RESOURCE_EXHAUSTED: exponential backoff starting at 30s, max 3 retries per job (quota — retriable)
- On 503 UNAVAILABLE: same backoff strategy (Gemini capacity issues are transient — retriable)
- On 400 INVALID_ARGUMENT: no retry — permanent user/config error (bad prompt, safety violation). Fail immediately with descriptive error
- Per-job retry is independent — one job's rate limit doesn't block others beyond the backoff delay
- After all retries exhausted, job marked as `failed` with `error_message="rate_limited"`
- Orchestrator logs each retry attempt with delay duration
- Unit tests for retry logic with fake adapter that simulates 429s

**Files affected:** `application/veo3_orchestrator.py` (sequential submit, retry logic), tests

### Story 18.4: Await Gate Auto-Retry & Failure Classification

As a pipeline developer,
I want the await gate to auto-retry all-failed job sets and distinguish transient from permanent failures,
so that a single transient error (missing SDK, rate limit burst) doesn't permanently fail the Veo3 integration.

**Acceptance criteria:**
- Existing `_all_jobs_failed()` check retained — triggers automatic re-submission when all jobs have `submit_failed` status
- New failure classification: `submit_failed` and `rate_limited` are retriable; `download_failed`, `generation_failed`, and `invalid_argument` are permanent
- Auto-retry fires at most once per await gate invocation (no infinite retry loops)
- After retry, polls normally until completion or timeout
- If retry submission also fails, proceeds without B-roll (emergency fallback)
- Await gate accepts `EventBus` in constructor and emits `veo3.gate.retried` event on auto-retry
- Unit tests for retry trigger conditions and single-retry guard

**Files affected:** `application/veo3_await_gate.py` (failure classification, retry guard, EventBus wiring), tests

### Story 18.5: QA Dispatch Timeout & Clink Fallback Wiring

As a pipeline developer,
I want QA dispatch timeouts properly wired through CLI and bootstrap, and the clink/Gemini fallback to work reliably,
so that QA evaluation doesn't timeout on slow hardware and token costs are optimized.

**Acceptance criteria:**
- `CliBackend` constructor accepts `dispatch_timeout_seconds` (already implemented)
- `bootstrap.py` passes `dispatch_timeout_seconds=max(300.0, settings.agent_timeout_seconds / 2)` to `CliBackend`
- `run_cli.py` already wires this — verify consistency with bootstrap path
- Clink fallback: try Gemini via clink first, check for JSON `{` in response, fall back to Claude Sonnet if not (already implemented — add test coverage)
- QA prompt size: `_MAX_INLINE_BYTES=15000` and summary-only for `face-position-map.json`, `speaker-timeline.json` (already implemented — add test coverage)
- Integration tests for timeout propagation and fallback path

**Files affected:** `app/bootstrap.py` (dispatch timeout wiring), `infrastructure/adapters/claude_cli_backend.py` (test coverage), `application/reflection_loop.py` (test coverage), tests

## Epic 19: B-Roll Assembly Engine

Replace the broken single-pass overlay approach in `reel_assembler.py` with a proven two-pass technique. Pass 1 builds the base reel (segments + xfade transitions). Pass 2 overlays B-roll clips at correct timeline positions using PTS-offset + `eof_action=pass`. Auto-upscales clips to match segment dimensions. This is the foundation both Veo3 and external documentary clips depend on.

**Technical insight source:** Production debugging on 2026-02-25 — single-pass `overlay=enable='between(t,...)'` fails after xfade chain due to timestamp domain shift. Two-pass PTS-offset approach (`setpts=PTS-STARTPTS+OFFSET/TB` + `overlay eof_action=pass`) verified working.

**Implementation order:** 19.1 → 19.2 → 19.3 → 19.4

### Story 19.1: Two-Pass Assembly Architecture

As a pipeline developer,
I want `reel_assembler.py` to use a two-pass approach for B-roll overlay assembly,
so that documentary cutaways appear at full opacity at correct timeline positions.

**Acceptance criteria:**
- `assemble_with_broll()` refactored into two explicit passes:
  - **Pass 1:** `assemble()` builds base reel from segments with xfade transitions → writes temp file
  - **Pass 2:** New `_overlay_broll()` method reads base reel + B-roll clips → overlays using PTS-offset technique → writes final output
- PTS-offset overlay: each B-roll clip gets `setpts=PTS-STARTPTS+{insertion_point}/TB` to place it at the correct timeline position
- Overlay chain: `[0:v][clip1]overlay=eof_action=pass[v1]; [v1][clip2]overlay=eof_action=pass[v2]; ...`
- Audio from base reel only: `-map '[v]' -map '0:a'` — B-roll clips contribute video only (documentary cutaway model)
- Temp file cleanup after successful pass 2
- Falls back to base reel (no B-roll) if pass 2 fails
- Existing `_build_cutaway_filter()` method removed or deprecated (broken approach)
- Integration tests: verify full opacity at overlay timestamps via frame extraction + pixel comparison

**Files affected:** `infrastructure/adapters/reel_assembler.py` (two-pass refactor), tests

### Story 19.2: Auto-Upscale B-Roll Clips

As a pipeline developer,
I want B-roll clips automatically upscaled to match the base reel's dimensions before overlay,
so that resolution mismatches (e.g., Veo3 720x1280 vs segments 1080x1920) don't cause visual artifacts.

**Acceptance criteria:**
- New `_ensure_clip_resolution()` method in `reel_assembler.py`: probes clip dimensions via ffprobe, scales to target if mismatched
- Uses `scale={w}:{h}:flags=lanczos` for quality upscaling
- Scaling happens before overlay pass (pre-processing step), not inside the filter graph
- Upscaled clips written to temp directory, cleaned up after assembly
- If clip is already at target resolution, skip scaling (no-op fast path)
- Target resolution hardcoded to 1080x1920 (canonical vertical Reel format) — no inference from segments
- Unit tests for resolution detection, scaling command construction, no-op path

**Files affected:** `infrastructure/adapters/reel_assembler.py` (upscale method), tests

### Story 19.3: B-Roll Fade Transitions

As a pipeline developer,
I want B-roll clips to fade in/out smoothly at their insertion boundaries,
so that the cutaway transitions feel polished rather than jarring hard cuts.

**Acceptance criteria:**
- Each B-roll clip in the overlay pass gets `format=yuva420p,fade=t=in:st=0:d=0.5:alpha=1,fade=t=out:st={dur-0.5}:d=0.5:alpha=1` applied before the PTS shift
- Edge case: clips shorter than 1.0s get reduced fade duration `min(0.5, dur * 0.4)` to avoid overlapping fades
- Fade duration configurable (default 0.5s) via parameter on `_overlay_broll()`
- Fade only affects the video alpha channel — audio continues uninterrupted
- Integration test: extract frames at fade boundaries, verify gradual opacity change
- Unit test: short clip (0.8s) gets proportionally shorter fade

**Files affected:** `infrastructure/adapters/reel_assembler.py` (fade in overlay filter), tests

### Story 19.4: Assembly Report B-Roll Section

As a pipeline developer,
I want the assembly report to include detailed B-roll insertion metadata,
so that QA and debugging can verify which clips were placed where and identify any issues.

**Acceptance criteria:**
- `assembly-report.json` includes `broll_summary` section with:
  - `clips_inserted`: count of successfully overlaid clips
  - `placements[]`: for each clip — variant, clip_path, insertion_point_s, duration_s, narrative_anchor, original_resolution, upscaled (bool)
  - `assembly_method`: `"two_pass_overlay"` (distinguishes from legacy approach)
  - `pass_1_duration_ms`: time taken for base assembly
  - `pass_2_duration_ms`: time taken for overlay pass
- Report generated by `reel_assembler.py`, not by the agent
- Unit tests for report structure

**Files affected:** `infrastructure/adapters/reel_assembler.py` (report generation), tests

## Epic 20: Documentary Cutaway System

Pedro can enrich Reels with external documentary footage sourced from YouTube Shorts, user-provided URLs, or agent-discovered reference clips. The Content Creator agent suggests relevant external videos based on transcript topics. Users can also provide explicit clip URLs via CLI. All external clips merge with Veo3 clips into a unified B-roll manifest for the assembly engine (Epic 19).

**Dependencies:** Epic 19 (two-pass assembly engine) must be complete before 20.6
**Implementation order:** 20.1 → 20.2 → 20.3 → (20.4 parallel with 20.5) → 20.6

### Story 20.1: External Clip Download & Preparation

As a pipeline developer,
I want a service that downloads external video clips from YouTube Shorts (and arbitrary URLs) and prepares them for overlay,
so that external documentary footage can be integrated into the assembly pipeline.

**Acceptance criteria:**
- New `infrastructure/adapters/external_clip_downloader.py` with `ExternalClipDownloader` class
- `download(url: str, dest_dir: Path) -> Path | None`: downloads video via `yt-dlp` subprocess (YouTube, TikTok, direct URLs)
- Return type: `Path` on success, `None` on failure (not pipeline-fatal)
- Strips audio track (`-an`) — documentary cutaways use base reel audio only
- Upscales to 1080x1920 if needed (reuses logic from Story 19.2 or delegates to reel_assembler)
- Validates: file exists, is valid video (ffprobe check), duration > 0
- Returns path to prepared clip in `external_clips/` subfolder of workspace
- Handles yt-dlp failures gracefully: logs warning, returns `None` (clip skipped, not pipeline-fatal)
- `ExternalClipDownloaderPort` protocol in `domain/ports.py` for testability
- Fake implementation for tests
- Unit tests for download command construction, error handling

**Files affected:** `infrastructure/adapters/external_clip_downloader.py` (new), `domain/ports.py` (ExternalClipDownloaderPort), tests

### Story 20.2: Cutaway Manifest Domain Model

As a pipeline developer,
I want a unified `CutawayManifest` domain model that merges Veo3 clips and external clips into a single ordered list for assembly,
so that the assembly engine has one consistent interface regardless of clip source.

**Acceptance criteria:**
- New `CutawayClip` frozen dataclass in `domain/models.py`: `source` (enum: `veo3`, `external`, `user_provided`), `variant`, `clip_path`, `insertion_point_s`, `duration_s`, `narrative_anchor`, `match_confidence`
- New `CutawayManifest` frozen dataclass: `clips: tuple[CutawayClip, ...]`, ordered by `insertion_point_s`
- Factory method `CutawayManifest.from_broll_and_external(broll: tuple[BrollPlacement, ...], external: tuple[CutawayClip, ...]) -> CutawayManifest` — merges, sorts, detects overlaps
- Overlap detection: if two clips overlap in time, the one with higher `match_confidence` wins; tie-break by source priority: `user_provided` > `veo3` > `external`. Dropped clip logged at WARNING level
- Overlap detection is a pure domain function (no I/O, no logging side effects) — returns `(kept, dropped)` tuple; caller handles logging
- `reel_assembler.assemble_with_broll()` updated to accept `CutawayManifest` instead of `tuple[BrollPlacement, ...]`
- Backward compatible: existing `BrollPlacement` converts to `CutawayClip` with `source=veo3`
- Unit tests for merge, sort, overlap resolution, tie-break priority

**Files affected:** `domain/models.py` (CutawayClip, CutawayManifest), `infrastructure/adapters/reel_assembler.py` (accept CutawayManifest), tests

### Story 20.3: CLI --cutaway Flag for User-Provided Clips

As a pipeline user,
I want to provide external video URLs via `--cutaway` CLI flag with target timestamps,
so that I can manually specify documentary footage to insert at specific narrative moments.

**Acceptance criteria:**
- New CLI flag: `--cutaway URL@TIMESTAMP` (repeatable), e.g., `--cutaway 'https://youtube.com/shorts/abc@30'`
- Parses URL and insertion timestamp by splitting on the **last** `@` character (URLs can contain `@` in paths/userinfo), e.g., `https://example.com/@user/video@30` → URL=`https://example.com/@user/video`, timestamp=`30`
- Downloads each clip via `ExternalClipDownloader` during pipeline setup (before stage 1)
- Clip duration auto-detected from downloaded file via ffprobe
- Creates `external_clips/cutaway-{n}.mp4` files in workspace
- Writes `external-clips.json` manifest: `[{url, clip_path, insertion_point_s, duration_s}]`
- Assembly stage reads `external-clips.json` + `veo3/jobs.json` → builds unified `CutawayManifest`
- If download fails for one URL, others still proceed (partial success)
- Help text documents the format and examples

**Files affected:** `scripts/run_cli.py` (--cutaway flag, download orchestration), `external-clips.json` (new manifest), tests

### Story 20.4: Content Creator Agent External Clip Suggestions

As a pipeline user,
I want the Content Creator agent to suggest relevant external reference clips based on transcript topics,
so that documentary footage is automatically discovered without manual URL hunting.

**Acceptance criteria:**
- Content Creator agent prompt updated: after generating `veo3_prompts`, also generates `external_clip_suggestions[]`
- Each suggestion: `{search_query, narrative_anchor, expected_content, duration_s, insertion_point_description}`
- Agent uses transcript context to identify moments where real-world footage would enhance the narrative
- Suggestions are advisory — a downstream service resolves them to actual URLs
- `publishing-assets.json` schema extended with `external_clip_suggestions[]` array
- QA gate validates suggestion structure (has search_query, has narrative_anchor)
- Agent generates 0-3 suggestions (conservative — quality over quantity)

**Files affected:** `workflows/stages/stage-04-content.md` (agent prompt update), `publishing-assets.json` schema, tests

### Story 20.5: External Clip Search & Resolution

As a pipeline developer,
I want a service that resolves Content Creator clip suggestions into downloadable URLs by searching YouTube,
so that agent-suggested documentary clips are automatically sourced without user intervention.

**Acceptance criteria:**
- New `application/external_clip_resolver.py` with `ExternalClipResolver` class
- `resolve(suggestion: dict) -> str | None`: uses `yt-dlp --flat-playlist "ytsearch1:{query}"` to find top YouTube Short matching the search query
- Filters: vertical format (Shorts), duration under 60s, relevance
- Returns URL of best match, or None if no suitable result found
- Launched as a fire-and-forget `asyncio.Task` by `pipeline_runner` after Content stage, alongside Veo3 generation
- Task stored in `PipelineRunner._background_tasks` dict for lifecycle management (cancel on pipeline abort, await on assembly)
- Downloads resolved clips via `ExternalClipDownloader` (Story 20.1)
- Writes resolved clips to `external_clips/` with manifest
- Rate-limited: max 3 searches per run, 2s delay between searches
- Falls back gracefully: if YouTube search fails, external clips are simply not included
- Task exception handling: unhandled errors logged + result set to empty (no clips), never crashes pipeline

**Files affected:** `application/external_clip_resolver.py` (new), `application/pipeline_runner.py` (background task lifecycle), tests

### Story 20.6: Unified Assembly Integration

As a pipeline developer,
I want the assembly stage to merge Veo3 clips and external documentary clips into a single cutaway manifest and overlay them in the final reel,
so that all B-roll sources are handled consistently with correct timeline placement.

**Acceptance criteria:**
- Assembly stage (pipeline_runner or stage 7 agent) reads both `veo3/jobs.json` and `external-clips.json`
- Converts both to `CutawayClip` instances, builds `CutawayManifest` via factory method
- Passes manifest to `reel_assembler.assemble_with_broll()`
- Assembly report `broll_summary.placements[]` includes source field (`veo3` vs `external` vs `user_provided`)
- Works with any combination: Veo3 only, external only, both, neither
- Pipeline runner wires external clip download as background task after CONTENT stage (parallel with Veo3)
- Await gate waits for both Veo3 and external clip background tasks before proceeding to assembly
- Cross-epic dependency: requires Epic 19 (two-pass assembly) and Stories 20.1-20.2 (downloader + manifest model)
- Integration tests for all source combinations

**Files affected:** `application/pipeline_runner.py` (unified manifest construction, background task await), `infrastructure/adapters/reel_assembler.py` (accepts CutawayManifest), `application/veo3_await_gate.py` (wait for external clips too), tests

## Epic 21: Additional Creative Instructions

**Goal:** Enable users to pass creative directives (images, videos, transitions, narrative changes) via the CLI, with the pipeline interpreting, validating, and applying them across relevant stages. Includes a full CLI refactoring to Command pattern for scalability.

**Global rule:** No source file in `src/` or `scripts/` exceeds 500 lines. Test files are exempt.

**FRs covered:** FR-AI1, FR-AI2, FR-AI3, FR-AI4, FR-AI5, FR-AI6, FR-AI7, FR-AI8
**NFRs addressed:** NFR-AI1, NFR-AI2
**Dependencies:** Epic 20 (cutaway manifest), Epics 12-13 (transitions/styles)

### Story 21.1: CLI Command Infrastructure — Protocols, Context, Invoker, History

As a pipeline developer,
I want a Command pattern infrastructure with protocols, a shared context, an invoker, and command history,
so that the CLI has a scalable, testable foundation where each concern is isolated and all executions are traceable.

**Acceptance criteria:**
- New package `src/pipeline/application/cli/` with `protocols.py`, `context.py`, `invoker.py`, `history.py`
- `protocols.py` defines `Command` protocol with `name` property and `async execute(context) -> CommandResult`, `StageHook` protocol with `should_run(stage, phase) -> bool` and `async execute(context) -> None`, `InputReader` protocol abstracting stdin, `ClipDurationProber` protocol abstracting ffprobe
- `context.py` defines `PipelineContext` dataclass holding: workspace, artifacts, settings, stage_runner, event_bus, and accumulated state — replaces the current 11-argument `run_pipeline()` signature
- `invoker.py` defines `PipelineInvoker` that executes commands, records results in `CommandHistory`, catches and records exceptions with status `failed` before re-raising
- `history.py` defines `CommandHistory` — debug stack persisted to `command-history.json` in workspace via atomic write, queryable: list all, filter by status, get last N
- `domain/models.py` extended with `CommandRecord` frozen dataclass: `name: str`, `started_at: str`, `finished_at: str`, `status: str`, `error: str | None` — uses `tuple` per project conventions
- `infrastructure/adapters/ffprobe_adapter.py` (new) implements `ClipDurationProber` protocol, extracts current `_probe_clip_duration` logic — only file that depends on `asyncio.create_subprocess_exec` for ffprobe
- `infrastructure/adapters/stdin_reader.py` (new) implements `InputReader` protocol, extracts current `_timed_input` logic — only file that depends on `sys.stdin`
- No source file exceeds 500 lines
- Comprehensive tests in `tests/unit/application/cli/`: `test_invoker.py`, `test_history.py`, `test_context.py`

**Files affected:** `application/cli/` (new package), `domain/models.py`, `infrastructure/adapters/ffprobe_adapter.py` (new), `infrastructure/adapters/stdin_reader.py` (new), tests

### Story 21.2: CLI Command Extraction — Commands, Hooks, Comprehensive Tests

As a pipeline developer,
I want each CLI concern extracted into its own ConcreteCommand and StageHook file with dependency injection,
so that every piece of logic is independently testable, no source file exceeds 500 lines, and the original `run_cli.py` becomes a thin composition root.

**Acceptance criteria:**
- Each command in its own file under `application/cli/commands/`:
  - `validate_args.py` — `ValidateArgsCommand`: validates CLI argument combinations, resolves defaults
  - `setup_workspace.py` — `SetupWorkspaceCommand`: creates new or opens resumed workspace, runs preflight
  - `download_cutaways.py` — `DownloadCutawaysCommand`: parses cutaway specs, downloads clips, writes manifest. Depends on `ClipDownloader` and `ClipDurationProber` protocols, not concrete classes
  - `run_elicitation.py` — `RunElicitationCommand`: interactive router Q&A loop. Depends on `InputReader` protocol, not `sys.stdin`
  - `run_stage.py` — `RunStageCommand`: runs a single pipeline stage through the reflection loop. Receives `tuple[StageHook, ...]` via constructor for pre/post hooks
  - `run_pipeline.py` — `RunPipelineCommand`: composes the above commands in sequence via the `PipelineInvoker`
- Each hook in its own file under `application/cli/hooks/`:
  - `veo3_fire_hook.py` — `Veo3FireHook`: fires Veo3 background task (post-Content)
  - `veo3_await_hook.py` — `Veo3AwaitHook`: awaits Veo3 completion (pre-Assembly)
  - `manifest_hook.py` — `ManifestBuildHook`: builds cutaway manifest (pre-Assembly)
  - `encoding_hook.py` — `EncodingPlanHook`: executes FFmpeg encoding plan (post-FFmpeg)
- Each hook implements `StageHook` protocol with `should_run()` self-selection — no if/elif chains in `RunStageCommand`
- All commands receive dependencies through constructor injection (protocols, not implementations)
- `scripts/run_cli.py` becomes a thin composition root (~50 lines): parse args, instantiate adapters, inject into commands, hand to invoker — zero business logic
- No source file in `src/` or `scripts/` exceeds 500 lines (test files exempt)
- Every command has its own test file in `tests/unit/application/cli/commands/`
- Every hook has its own test file in `tests/unit/application/cli/hooks/`
- Every branch covered: happy path, validation failures, partial failures, timeouts, non-interactive fallback, resume detection, empty workspace, all-stages-complete
- All tests use fakes/protocols for dependencies (no mocking of concrete classes)
- Existing test behavior from `test_run_cli.py`, `test_run_cli_atomic_write.py`, `test_cli_cutaway.py` preserved and reorganized

**Files affected:** `application/cli/commands/` (6 new files), `application/cli/hooks/` (4 new files), `scripts/run_cli.py` (rewrite), `tests/unit/application/cli/` (10+ new test files), old test files removed after migration

### Story 21.3: Instructions Flag & Domain Model

As a pipeline user,
I want to pass additional creative instructions via a `--instructions` flag when running the CLI,
so that I can provide specific directives about images, video clips, transitions, and narrative that shape the final short.

**Acceptance criteria:**
- `--instructions` added to `arg_parser.py` as an optional string argument
- `ValidateArgsCommand` validates the flag (non-empty when provided)
- Instructions string stored in `PipelineContext` and forwarded to the Router stage as input
- Omitting `--instructions` produces identical behavior to current pipeline runs
- Frozen dataclasses added to `domain/models.py`: `CreativeDirectives` (top-level container), `OverlayImage` (path, timestamp, duration), `DocumentaryClip` (path or query, placement hint), `TransitionPreference` (effect type, timing), `NarrativeOverride` (tone, structure, pacing, arc changes)
- All domain models use `tuple` (not list) and `Mapping` (not dict) per project conventions
- `CreativeDirectives` has class method `empty()` returning a no-op instance for backward compatibility
- No source file exceeds 500 lines
- Comprehensive tests: domain model constructors, immutability, `empty()` factory, CLI flag parsing, validation branches, backward compatibility

**Files affected:** `application/cli/arg_parser.py`, `application/cli/commands/validate_args.py`, `application/cli/context.py`, `domain/models.py`, tests

### Story 21.4: Router Directive Parsing & Validation

As a pipeline developer,
I want the Router agent to parse additional instructions into structured directive categories and validate referenced media files,
so that downstream agents receive clean, typed data and invalid references fail fast before expensive processing.

**Acceptance criteria:**
- Router agent extracts and categorizes directives into: `overlay_images`, `cutaway_clips`, `transition_preferences`, `narrative_overrides`
- Structured directives written as new fields in `router-output.json`
- Referenced local files (images, videos) validated for existence and accessibility at Router stage
- Invalid references flagged with warnings in `router-output.json` (non-fatal)
- Validation adds no more than 2 seconds to Router execution time (NFR-AI1)
- When no `--instructions` provided, `router-output.json` contains empty directive fields (backward compatible)
- Comprehensive tests: parsing each directive category, mixed directives, malformed input, missing files, empty instructions, backward compatibility, schema validation

**Files affected:** `workflows/stages/stage-01-router.md`, `agents/router/agent.md`, `application/cli/commands/run_stage.py` (forwards instructions), tests

### Story 21.5: Content Creator Narrative Overrides

As a pipeline user,
I want the Content Creator agent to apply my narrative directives (tone, structure, pacing, story arc),
so that the generated descriptions, hashtags, and content direction reflect my creative vision.

**Acceptance criteria:**
- Content Creator stage (Stage 4) reads `narrative_overrides` from `router-output.json`
- Agent adjusts: tone (e.g. humorous, dramatic, educational), structure (e.g. hook-first, chronological), pacing cues, story arc modifications
- Generated `content.json` reflects the overrides
- When no narrative overrides exist, behavior is identical to current pipeline (backward compatible)
- Comprehensive tests: each override type, combined overrides, empty overrides, partial overrides, backward compatibility

**Files affected:** `workflows/stages/stage-04-content.md`, `agents/content-creator/agent.md`, tests

### Story 21.6: FFmpeg Transition & Image Overlay Directives

As a pipeline user,
I want the FFmpeg Engineer agent to apply my transition effects and overlay images at specified moments,
so that the final short includes the visual style I requested.

**Acceptance criteria:**
- FFmpeg Engineer stage (Stage 6) reads `transition_preferences` from `router-output.json` and incorporates user-specified transitions (fades, wipes, dissolves) into `encoding-plan.json`
- User transitions override default style-change transitions at specified points
- FFmpeg Engineer reads `overlay_images` from `router-output.json` and adds FFmpeg overlay filter commands to `encoding-plan.json` for each image at specified timestamp and duration
- Images validated (format, resolution) before inclusion
- When no transition or image directives exist, behavior is identical to current pipeline (backward compatible)
- Comprehensive tests: custom transitions, image overlays, combined directives, invalid images, missing files, conflicting transitions, backward compatibility

**Files affected:** `workflows/stages/stage-06-ffmpeg-engineer.md`, `agents/ffmpeg-engineer/agent.md`, `infrastructure/adapters/ffmpeg_adapter.py` (overlay support), tests

### Story 21.7: Assembly Documentary Clip Integration

As a pipeline user,
I want the Assembly stage to incorporate user-provided documentary-style video clips into the final short,
so that my additional video content is woven into the reel at the specified moments.

**Acceptance criteria:**
- Assembly stage (Stage 7) reads `cutaway_clips` directives from `router-output.json`
- User-provided documentary clips added to `CutawayManifest` (Epic 20) with source type `user_instructed`
- Clips placed at user-specified insertion points
- Assembly report `broll_summary.placements[]` includes source field
- Documentary clips referenced by URL are downloaded via `ExternalClipDownloader` (Epic 20 infrastructure)
- When no documentary clip directives exist, behavior is identical to current pipeline (backward compatible)
- Comprehensive tests: user-provided clips, URL-referenced clips, mixed sources (Veo3 + external + user), no-clips, integration with Epic 20 `CutawayManifest`

**Files affected:** `application/cli/hooks/manifest_hook.py` (extend for user clips), `infrastructure/adapters/reel_assembler.py`, `workflows/stages/stage-07-assembly.md`, tests
