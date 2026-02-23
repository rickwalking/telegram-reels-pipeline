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

## Epic List

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
