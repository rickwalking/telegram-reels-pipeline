---
stepsCompleted: [step-01-init, step-02-context, step-03-starter, step-04-decisions, step-05-patterns, step-06-structure, step-07-validation, step-08-complete]
lastStep: 8
status: 'complete'
completedAt: '2026-02-10'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/prd-validation-report.md
  - _bmad-output/planning-artifacts/product-brief-telegram-reels-pipeline-2026-02-10.md
  - _bmad-output/planning-artifacts/research/technical-telegram-mcp-claude-code-integration-research-2026-02-09.md
workflowType: 'architecture'
project_name: 'Telegram Reels Pipeline'
user_name: 'Pedro'
date: '2026-02-10'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
43 FRs across 8 capability areas. Architecturally significant groupings:
- **Inbound interface** (FR1-FR4): Telegram trigger, elicitation, queue notification — drives MessagingPort and queue consumer design
- **AI processing chain** (FR5-FR9, FR17-FR19): Episode analysis, moment selection, content generation — drives AgentExecutionPort and model routing
- **Video pipeline** (FR10-FR16): Layout detection, crop strategies, knowledge base learning — drives VideoProcessingPort, knowledge store, and escalation flow
- **Quality assurance** (FR20-FR24): Prescriptive QA gates, best-of-three, escalation — drives ReflectionLoop and ModelDispatchPort
- **Delivery & revision** (FR25-FR34): Telegram delivery, 4 revision types, incremental re-delivery — drives Router Agent feedback interpretation and targeted re-processing
- **Infrastructure** (FR35-FR43): Checkpoints, crash recovery, queue, resource monitoring, operations — drives StateStore, EventBus, WorkspaceManager, QueueConsumer

**Non-Functional Requirements:**
22 NFRs shaping architectural decisions:
- **Performance**: 20-45 min e2e, 3GB memory cap, 80% CPU cap, tmpfs for video intermediates
- **Reliability**: 90% completion rate, 60s crash recovery, atomic state writes, watchdog heartbeat
- **Integration**: 50MB Telegram limit (Google Drive fallback), rate limit compliance, MCP lifecycle management
- **Security**: Environment-variable secrets, CHAT_ID auth, 600/700 file permissions, no open ports

**Scale & Complexity:**
- Primary domain: Backend pipeline service (daemon)
- Complexity level: Medium
- Estimated architectural components: 8 core (FSM, AgentExecutor, ReflectionLoop, ModelRouter, RecoveryChain, EventBus, WorkspaceManager, QueueConsumer)

### Technical Constraints & Dependencies

- **Hardware**: Raspberry Pi (ARM aarch64), 4GB+ RAM, shared with Umbrel services
- **Runtime**: Python 3.11+ async daemon under systemd
- **AI backbone**: Claude Code CLI (Phase 1) → Agent SDK (Phase 2), Claude MAX subscription
- **Messaging**: Telegram MCP (qpd-v/mcp-communicator-telegram) — `ask_user`, `notify_user`, `send_file`
- **Multi-model**: PAL MCP for routing QA to Gemini/o4-mini/Codex
- **Video tools**: FFmpeg (thread-capped), yt-dlp
- **File delivery**: Telegram Bot API (≤50MB), Google Drive (>50MB fallback)
- **State**: File-based (markdown frontmatter + JSON), no database

### Cross-Cutting Concerns Identified

- **Crash recovery & checkpointing** — affects every pipeline stage (atomic writes, session persistence, resume logic)
- **Resource awareness** — memory/CPU/thermal checks gate FFmpeg and agent execution
- **QA gate enforcement** — every stage must pass QA before forward transition
- **Event observability** — all state transitions logged for debugging and operations
- **Error recovery** — 6-level fallback chain applies to every agent execution
- **Session management** — per-agent session IDs for resume/fork, independent QA sessions
- **Telegram communication** — status notifications, escalations, and delivery span the entire pipeline

## Starter Template Evaluation

### Primary Technology Domain

Python backend pipeline service (daemon) — no web framework or UI starter applicable.

### Starter Options Considered

| Option | Assessment |
|--------|-----------|
| **cookiecutter-pypackage** | Generic Python package template — too broad, doesn't address hexagonal architecture or async daemon patterns |
| **cookiecutter-hypermodern-python** | Modern Python with strict typing, testing, linting — closest match but still oriented toward library distribution, not daemon services |
| **Manual scaffolding** | From-scratch project structure following the Hexagonal Architecture defined in technical research — full control, exact fit |

### Selected Approach: Manual Scaffolding

**Rationale:** The technical research document already defines a detailed project structure, tooling configuration, coding standards, and architectural patterns specific to this pipeline service. No existing Python starter template provides Hexagonal Architecture with the 8 Port Protocols, systemd integration, and BMAD-native file state management this project requires. Manual scaffolding from the research-validated structure is the cleanest path.

**Dependency Management: Poetry**

Poetry manages virtual environments, dependency resolution, and packaging. All dependencies defined in `pyproject.toml`, locked in `poetry.lock`.

**Initialization Command:**

```bash
# Project scaffolding (first implementation story)
poetry init --name telegram-reels-pipeline --python "^3.11"
poetry add pydantic pyyaml python-telegram-bot aiofiles
poetry add --group dev black isort ruff mypy pytest pytest-asyncio pytest-cov
mkdir -p src/pipeline/{domain,application,infrastructure/adapters,app}
mkdir -p tests/{unit/{domain,application},integration}
mkdir -p config
touch src/pipeline/__init__.py src/pipeline/{domain,application,infrastructure,app}/__init__.py
```

### Architectural Decisions Provided by Scaffolding

**Language & Runtime:**
Python 3.11+, async/await for I/O-bound work, synchronous for pure transforms

**Tooling Configuration:**
black (line-length=120), isort (black profile), ruff (py311, C901 enforced), mypy --strict (Any banned), pytest (asyncio_mode=auto, 80% coverage minimum)

**Code Organization:**
Hexagonal Architecture — Domain (pure core, stdlib only) → Application (use cases, domain imports only) → Infrastructure (adapters, third-party libs) → Composition Root (wiring)

**Testing Framework:**
pytest + pytest-asyncio + pytest-cov, AAA pattern, fakes over mocks for domain collaborators, contract tests for Protocol implementations, property tests for pure transforms

**Development Experience:**
Poetry for dependency management and virtual environments, .editorconfig, pyproject.toml as single config file (tool configs + Poetry deps), Pydantic BaseSettings for configuration, .env for secrets

**Note:** Project initialization using this scaffolding should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Hexagonal Architecture with 4 layers and 8 Port Protocols
- Orchestrator-Worker FSM with State Pattern (transition table + guards)
- Claude Code CLI for Phase 1 agent execution (SDK migration in Phase 2)
- File-based state persistence (markdown frontmatter + JSON)
- Telegram MCP (qpd-v) as sole external interface

**Important Decisions (Shape Architecture):**
- Generator-Critic reflection loop for QA gates (max 3 attempts, best-of-three)
- 6-level error recovery Chain of Responsibility
- PAL MCP multi-model routing (Gemini for deep QA, o4-mini for light QA)
- In-process EventBus for decoupled observability
- Per-run isolated workspaces with atomic checkpoint writes

**Deferred Decisions (Post-MVP):**
- Agent SDK migration (Phase 2) — CLI proven first
- Video processing sub-agent decomposition (Phase 2) — monolithic first
- Multi-model QA escalation chain (Phase 2) — single model first
- Saved profiles and Episode Scanner mode (Phase 2 features)

### Data Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Run state** | Markdown frontmatter (YAML) in `run.md` | BMAD-native, human-readable, parseable |
| **Session tracking** | JSON (`sessions.json`) | Structured data, easy programmatic access |
| **Event journal** | Append-only plaintext (`events.log`) | Simple, grep-friendly, no corruption risk |
| **Knowledge base** | YAML (`crop-strategies.yaml`) | Human-editable, complex nested structures |
| **Queue items** | JSON files with timestamp prefix | Atomic write + rename, natural FIFO ordering |
| **Configuration** | YAML (`config/*.yaml`) + Pydantic BaseSettings | YAML for human editing, Pydantic for validation |
| **Artifacts** | Raw files in per-run `assets/` directory | Videos, transcripts, screenshots as native formats |
| **Database** | None — file-based only | Single-user POC, no query requirements |

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **User auth** | Telegram `CHAT_ID` whitelist (single value) | Single-user POC, simplest possible auth |
| **Secret management** | `.env` file loaded via systemd `EnvironmentFile` | Standard systemd pattern, no secrets in code/config |
| **MCP isolation** | stdio transport, process-scoped per run | No network exposure, ephemeral per pipeline run |
| **File permissions** | 600 for secrets/state, 700 for directories | Restrict to pipeline service user only |
| **Input validation** | URL validation at inbound boundary only | Reject non-YouTube URLs at queue entry |
| **Network exposure** | Zero open ports — Telegram polling only | No HTTP server, no inbound connections |

### Communication Patterns

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **External interface** | Telegram MCP only — no HTTP API, no CLI | PRD: message-driven interaction model |
| **Agent-to-agent** | Via orchestrator (no direct communication) | FSM enforces stage ordering; artifacts shared via filesystem |
| **Event distribution** | In-process EventBus (Observer pattern) | Decouples logging, notification, checkpointing |
| **Revision routing** | Router Agent interprets feedback → targeted agent | 4 revision types: extend, fix framing, different moment, add context |

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Process management** | systemd (Restart=always, RestartSec=30, WatchdogSec=300) | Auto-start, auto-restart, resource limits, watchdog |
| **Resource limits** | MemoryMax=3G, CPUQuota=80%, FFmpeg `-threads 2` | Leave headroom for Umbrel services |
| **Temp storage** | tmpfs for video intermediates | Reduce SD card wear |
| **Disk cleanup** | Run assets deleted after 30 days, final Reels + metadata kept | Balance storage vs. audit trail |
| **Logging** | Per-run `events.log` + systemd journal | No external logging service |
| **Monitoring** | systemd watchdog + Telegram failure notification | Minimal ops overhead |
| **Dependency mgmt** | Poetry (virtual env, resolution, lock file) | Reproducible builds, single `poetry install` for all deps |
| **CI/CD** | Local development, manual deploy to Pi | Solo developer POC |

### Phase Boundaries

| Capability | Phase 1 (MVP) | Phase 2 (Growth) |
|-----------|---------------|------------------|
| **Agent execution** | Claude Code CLI (`claude -p`) | Agent SDK (Python `query()`) |
| **Session mgmt** | `--resume <session_id>` flag | SDK session capture in code |
| **Error recovery** | Levels 1-3 + 6 (retry, fork, fresh, escalate) | Full 6-level chain with backend swap |
| **QA routing** | Single model (Gemini via PAL MCP) | Multi-model with escalation chain |
| **Video processing** | Monolithic | Decomposed sub-agents |

### Decision Impact Analysis

**Implementation Sequence:**
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

**Cross-Component Dependencies:**
- FSM depends on: Domain types, state persistence
- Agent executor depends on: Domain ports, model router
- Reflection loop depends on: Agent executor, model router
- Recovery chain depends on: Agent executor, messaging port
- Queue consumer depends on: FSM, workspace manager, event bus
- All infrastructure adapters depend on: Domain port definitions

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

12 areas where AI agents could make incompatible choices, organized into 5 categories.

### Naming Patterns

**Python Code (confirmed from research):**
- Variables/functions: `snake_case` — `pipeline_state`, `calculate_crop_region`
- Classes: `PascalCase` — `PipelineOrchestrator`, `QAReflectionLoop`
- Constants: `UPPER_SNAKE_CASE` — `MAX_QA_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS`
- Enums: `PascalCase` class, `UPPER_CASE` members — `PipelineStage.QA_CONTENT`
- Modules: `snake_case` — `state_machine.py`, `model_router.py`
- Private: `_leading_underscore` — `_validate_transition`
- Full words over abbreviations: `context` not `ctx`, `repository` not `repo`
- Universal acronyms allowed: `llm`, `mcp`, `qa`, `api`, `url`

**File & Directory Naming:**
- Source modules: `snake_case.py` — `state_machine.py`, `agent_executor.py`
- Test files: `test_<module>.py` — `test_state_machine.py`
- Config files: `kebab-case.yaml` — `crop-strategies.yaml`, `quality-gates.yaml`
- Run directories: `<timestamp>-<short_id>` — `2026-02-10-abc123`
- Checkpoint files: `<stage>-output.md` — `router-output.md`, `research-output.md`

**Event Naming:**
- Format: `snake_case` with dot-separated namespace — `pipeline.stage_entered`, `qa.gate_passed`, `error.recovered`
- Always past tense for completed events — `stage_entered` not `stage_enter`
- Prefix with subsystem — `pipeline.*`, `qa.*`, `error.*`, `telegram.*`

### Structure Patterns

**Hexagonal Layer Rules (enforced by imports):**

| Layer | Can Import | Cannot Import |
|-------|-----------|--------------|
| `domain/` | stdlib only | application, infrastructure, app |
| `application/` | domain | infrastructure, app |
| `infrastructure/` | domain, application, third-party | app |
| `app/` | all layers | — |

**Test Organization:**
- `tests/unit/domain/` — pure function tests, no I/O mocks
- `tests/unit/application/` — use case tests with faked ports
- `tests/integration/` — real adapters against real tools (FFmpeg, filesystem)
- Test naming: `test_<unit>_<scenario>_<expected>` — `test_fsm_qa_pass_transitions_to_next_stage`

**Config Organization:**
- `config/pipeline.yaml` — pipeline settings (timeframes, thresholds, model routing)
- `config/crop-strategies.yaml` — layout knowledge base (self-expanding)
- `config/quality-gates.yaml` — per-gate validation criteria
- `.env` — secrets only (tokens, API keys, CHAT_ID)

### Format Patterns

**Frontmatter Schema (run.md) — all agents MUST use this exact schema:**
```yaml
---
run_id: "<timestamp>-<short_id>"
youtube_url: "<url>"
current_stage: "<PipelineStage enum value in snake_case>"
current_attempt: <int>
qa_status: "pending | passed | rework | failed"
stages_completed: [<list of snake_case stage names>]
escalation_state: "none | layout_unknown | qa_exhausted | error_escalated"
best_of_three_overrides: [<list of gate names>]
created_at: "<ISO 8601>"
updated_at: "<ISO 8601>"
---
```

**QA Critique Schema (Pydantic-enforced across all models):**
```json
{
  "decision": "PASS | REWORK | FAIL",
  "score": 85,
  "gate": "<snake_case gate name>",
  "attempt": 2,
  "blockers": [{"severity": "critical | high | medium | low", "description": "..."}],
  "prescriptive_fixes": ["exact fix instruction 1"],
  "confidence": 0.92
}
```

**Event Log Format (events.log):**
```
2026-02-10T14:30:00Z | pipeline.stage_entered | router | {"attempt": 1}
2026-02-10T14:30:15Z | qa.gate_passed | router | {"score": 92, "attempt": 1}
```

### Communication Patterns

**Telegram Message Formatting:**
- Status updates: `"Processing stage {n}/{total}: {stage_name}..."`
- QA results: `"QA gate {gate}: {PASS|REWORK} (score: {score}/100)"`
- Escalation: screenshot/context + clear A/B/C options
- Delivery: video first → descriptions → hashtags + music
- Error: `"Pipeline paused: {description}. Resuming automatically..."` or `"Pipeline needs help: {description}"`

**Agent Prompt Contracts — standardized input bundle per agent:**
- `stage_requirements` — what this stage must produce
- `prior_artifacts` — outputs from completed stages (file paths, not inline)
- `elicitation_context` — user preferences from Router Agent
- `attempt_history` — prior attempts and QA feedback (for rework cycles)

### Process Patterns

**Atomic State Writes — all state mutations use write-to-temp + rename:**
```python
def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content)
    tmp.rename(path)  # atomic on same filesystem
```

**Checkpoint Timing:**
- Write AFTER each stage completes (not during)
- Write BEFORE QA gate starts (captures artifact to be reviewed)
- Never checkpoint mid-agent-execution (incomplete state)

**Error Propagation:**
- Domain errors: raise specific `PipelineError` subclass
- Never catch-and-silence: `except Exception: pass` is BANNED
- Always preserve cause: `raise ... from exc`
- Recovery chain handles all errors — components don't retry independently

**Async Boundaries:**
- `async` for: agent calls, file I/O, MCP tool calls, subprocess execution
- Synchronous for: pure transforms, crop calculations, schema validation, FSM transitions
- `asyncio.timeout()` for all bounded operations
- `asyncio.TaskGroup` for concurrent sub-tasks (Python 3.11+)

### Enforcement Guidelines

**All AI Agents MUST:**
1. Follow Hexagonal Architecture import rules — domain imports stdlib only
2. Use exact frontmatter schema for `run.md` — no field additions without Protocol update
3. Return QA critiques matching Pydantic-validated schema — violations trigger retry
4. Use `atomic_write` for all state file mutations — no direct `write_text` on state files
5. Emit events via EventBus for all state transitions — no silent transitions
6. Follow domain exception hierarchy — no bare `except:` or generic `Exception` catching

**Pattern Enforcement:**
- `mypy --strict` catches type violations at CI
- `ruff` catches complexity and style violations
- Pydantic `model_validate_json()` enforces QA schema at runtime
- Import linter rule enforces Hexagonal layer boundaries

## Project Structure & Boundaries

### Complete Project Directory Structure

```
telegram-reels-pipeline/
├── pyproject.toml                       # Poetry deps + tool config: black, isort, ruff, mypy, pytest
├── poetry.lock                          # Locked dependency versions (committed to git)
├── .editorconfig                        # Editor consistency
├── .env.example                         # Secret template (TELEGRAM_TOKEN, CHAT_ID, ANTHROPIC_API_KEY)
├── .gitignore
├── README.md
│
├── config/                              # Runtime configuration (YAML)
│   ├── pipeline.yaml                    # Timeframes, thresholds, model routing table
│   ├── crop-strategies.yaml             # Layout knowledge base (self-expanding)
│   ├── quality-gates.yaml               # Per-gate validation criteria, scoring thresholds
│   └── profiles.yaml                    # Named presets (Growth feature — empty for MVP)
│
├── systemd/                             # Deployment configuration
│   ├── telegram-reels-pipeline.service  # systemd unit file
│   └── telegram-reels-pipeline.env      # Environment file template
│
│── ─── BMAD WORKFLOW LAYER ─────────────────────────────────────────
│
├── workflows/                           # BMAD pipeline workflow
│   ├── workflow.md                      # BMAD WORKFLOW ENTRYPOINT
│   │                                    #   name, description, initialization,
│   │                                    #   config loading, agent resolution,
│   │                                    #   execution: "Read fully and follow: stages/stage-01-router.md"
│   ├── stages/                          # BMAD step files — self-contained, sequential
│   │   ├── stage-01-router.md           # Trigger parsing, elicitation, tier selection
│   │   ├── stage-02-research.md         # Episode metadata, context, topic analysis
│   │   ├── stage-03-transcript.md       # Moment selection, timestamp extraction
│   │   ├── stage-04-content.md          # Descriptions, hashtags, music suggestions
│   │   ├── stage-05-layout-detective.md # Frame extraction, layout classification, crop strategy
│   │   ├── stage-06-ffmpeg-engineer.md  # Crop, encode, segment processing
│   │   ├── stage-07-assembly.md         # Final Reel composition
│   │   └── stage-08-delivery.md         # Telegram delivery, content options
│   ├── revision-flows/                  # BMAD step files for revision entry points
│   │   ├── revision-extend-moment.md    # Widen timestamp window
│   │   ├── revision-fix-framing.md      # Correct crop on specific segment
│   │   ├── revision-different-moment.md # Re-run moment selection
│   │   └── revision-add-context.md      # Expand context before/after
│   └── qa/                              # QA gate step files
│       ├── qa-gate-template.md          # Shared QA execution rules + prescriptive feedback protocol
│       └── gate-criteria/               # Per-gate validation criteria
│           ├── router-criteria.md
│           ├── research-criteria.md
│           ├── transcript-criteria.md
│           ├── content-criteria.md
│           ├── layout-criteria.md
│           ├── ffmpeg-criteria.md
│           └── assembly-criteria.md
│
├── agents/                              # BMAD agent definitions
│   ├── router/
│   │   ├── agent.md                     # Persona, role, capabilities, output contract
│   │   ├── elicitation-flow.md          # Smart defaults, question logic, topic parsing
│   │   └── revision-interpretation.md   # 4 revision types mapping
│   ├── research/
│   │   ├── agent.md                     # Persona, research strategy
│   │   └── metadata-extraction.md       # YouTube metadata, channel context
│   ├── transcript/
│   │   ├── agent.md                     # Persona, selection criteria
│   │   └── moment-selection-criteria.md # Narrative structure, emotional peaks, quotable statements
│   ├── content-creator/
│   │   ├── agent.md                     # Persona, output formats
│   │   ├── description-style-guide.md   # Instagram description conventions, 3-option format
│   │   └── hashtag-strategy.md          # Hashtag selection, Portuguese/English mix
│   ├── layout-detective/
│   │   ├── agent.md                     # Persona, classification logic
│   │   ├── frame-analysis.md            # Key frame extraction and analysis
│   │   └── escalation-protocol.md       # Unknown layout → Telegram screenshot → learn
│   ├── ffmpeg-engineer/
│   │   ├── agent.md                     # Persona, FFmpeg expertise
│   │   ├── crop-playbook.md             # Per-layout crop strategies, safe zones, transitions
│   │   └── encoding-params.md           # Pi-optimized: threads, bitrate, codec settings
│   ├── qa/
│   │   ├── agent.md                     # Persona, evaluation framework
│   │   └── prescriptive-feedback.md     # How to write exact fix instructions
│   └── delivery/
│       ├── agent.md                     # Persona, delivery protocol
│       └── message-templates.md         # Telegram message structure for delivery sequence
│
│── ─── PYTHON APPLICATION LAYER ────────────────────────────────────
│
├── src/
│   └── pipeline/
│       ├── __init__.py
│       │
│       ├── domain/                      # LAYER 1: Pure core — stdlib only
│       │   ├── __init__.py
│       │   ├── types.py                 # NewType: RunId, AgentId, SessionId, GateName
│       │   ├── enums.py                 # PipelineStage, QADecision, EscalationState, RevisionType
│       │   ├── models.py               # Frozen dataclasses: AgentRequest, AgentResult, QACritique,
│       │   │                            #   CropRegion, VideoMetadata, QueueItem, RunState, PipelineEvent
│       │   ├── errors.py               # Exception hierarchy: PipelineError → ConfigurationError,
│       │   │                            #   ValidationError, AgentExecutionError, UnknownLayoutError
│       │   ├── ports.py                # 8 Port Protocols: AgentExecutionPort, ModelDispatchPort,
│       │   │                            #   MessagingPort, VideoProcessingPort, VideoDownloadPort,
│       │   │                            #   StateStorePort, FileDeliveryPort, KnowledgeBasePort
│       │   └── transitions.py          # FSM transition table + guard definitions (pure data)
│       │
│       ├── application/                 # LAYER 2: Use cases — imports domain only
│       │   ├── __init__.py
│       │   ├── orchestrator.py          # PipelineOrchestrator — FSM driver, stage dispatch
│       │   │                            #   Loads workflow step files, spawns Claude Code CLI,
│       │   │                            #   collects artifacts, drives QA gates
│       │   ├── state_machine.py         # PipelineStateMachine — transition execution + guards
│       │   ├── reflection_loop.py       # ReflectionLoop — Generator-Critic QA with best-of-three
│       │   ├── model_router.py          # ModelRouter — role-based model selection
│       │   ├── recovery_chain.py        # RecoveryChain — 6-level Chain of Responsibility
│       │   ├── event_bus.py             # EventBus — Observer pattern, publish/subscribe
│       │   ├── queue_consumer.py        # QueueConsumer — FIFO claim/ack/heartbeat
│       │   ├── workspace_manager.py     # WorkspaceFactory — per-run isolation + context manager
│       │   └── revision_router.py       # RevisionRouter — interpret feedback, route to agent
│       │
│       ├── infrastructure/              # LAYER 3: Adapters — imports domain + third-party
│       │   ├── __init__.py
│       │   ├── adapters/
│       │   │   ├── __init__.py
│       │   │   ├── claude_cli_backend.py    # CliBackend — subprocess `claude -p` execution
│       │   │   ├── claude_sdk_backend.py    # SdkBackend — Agent SDK query() (Phase 2)
│       │   │   ├── telegram_mcp_adapter.py  # TelegramMessaging — ask_user, notify_user, send_file
│       │   │   ├── pal_mcp_adapter.py       # PalModelDispatch — codereview, chat, consensus
│       │   │   ├── ffmpeg_adapter.py        # FFmpegProcessor — crop, encode, validate
│       │   │   ├── ytdlp_adapter.py         # YtDlpDownloader — metadata, subtitles, video
│       │   │   ├── file_state_store.py      # FileStateStore — frontmatter read/write, atomic ops
│       │   │   ├── google_drive_adapter.py  # GoogleDriveUploader — >50MB file delivery
│       │   │   └── knowledge_base_adapter.py # YamlKnowledgeBase — crop-strategies.yaml CRUD
│       │   ├── listeners/
│       │   │   ├── __init__.py
│       │   │   ├── event_journal_writer.py      # Append-only events.log writer
│       │   │   ├── frontmatter_checkpointer.py  # run.md frontmatter updater
│       │   │   ├── telegram_notifier.py         # Status updates on stage transitions
│       │   │   └── resource_monitor.py          # Memory/CPU/thermal check before FFmpeg
│       │   └── telegram_bot/
│       │       ├── __init__.py
│       │       ├── polling_listener.py      # Telegram polling loop — receives URLs, enqueues
│       │       └── url_validator.py         # YouTube URL validation at inbound boundary
│       │
│       └── app/                         # LAYER 4: Composition root — imports all layers
│           ├── __init__.py
│           ├── main.py                  # Entry point: systemd ExecStart target
│           ├── bootstrap.py             # create_orchestrator() — wires all dependencies
│           └── settings.py              # Pydantic BaseSettings — loads .env + config/*.yaml
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures: fake ports, test workspace factory
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── test_models.py           # Frozen dataclass construction, validation
│   │   │   ├── test_transitions.py      # Transition table completeness, guard logic
│   │   │   └── test_enums.py            # Enum coverage, stage ordering
│   │   └── application/
│   │       ├── __init__.py
│   │       ├── test_state_machine.py    # FSM transitions with faked state store
│   │       ├── test_reflection_loop.py  # QA loop with faked executor + critic
│   │       ├── test_recovery_chain.py   # Handler ordering, escalation
│   │       ├── test_event_bus.py        # Publish/subscribe, listener isolation
│   │       ├── test_queue_consumer.py   # FIFO ordering, dedup, lock behavior
│   │       ├── test_workspace_manager.py # Isolation, cleanup, checkpoint
│   │       └── test_revision_router.py  # 4 revision type routing
│   └── integration/
│       ├── __init__.py
│       ├── test_file_state_store.py     # Real filesystem atomic writes
│       ├── test_ffmpeg_adapter.py       # Real FFmpeg crop/encode (small test video)
│       ├── test_ytdlp_adapter.py        # Real yt-dlp metadata extraction
│       └── test_workspace_lifecycle.py  # Full workspace create → checkpoint → cleanup
│
├── workspace/                           # Runtime data (gitignored)
│   ├── runs/                            # Per-run isolated workspaces
│   ├── queue/                           # FIFO queue directories
│   │   ├── inbox/
│   │   ├── processing/
│   │   └── completed/
│   └── knowledge/                       # Self-expanding layout knowledge
│
└── scripts/                             # Development utilities
    ├── install.sh                       # Setup: poetry install, systemd unit
    └── cleanup.sh                       # Disk cleanup: runs older than 30 days
```

### Architectural Boundaries

**Two-Layer Architecture — BMAD Workflow + Python Orchestrator:**

```
┌─────────────────────────────────────────────────────────┐
│              BMAD WORKFLOW LAYER (markdown)               │
│  workflow.md → stage step files → agent definitions       │
│  Claude Code CLI reads and executes these directly        │
│  Domain knowledge, personas, criteria live here           │
└─────────────────────┬───────────────────────────────────┘
                      │ orchestrator spawns CLI with step file as prompt
┌─────────────────────▼───────────────────────────────────┐
│           PYTHON APPLICATION LAYER (code)                 │
│  Orchestrator (FSM) → Agent Executor → QA Loop            │
│  State persistence, queue management, error recovery      │
│  Decides WHICH step file to run, not WHAT the agent does  │
└─────────────────────────────────────────────────────────┘
```

**Port Boundaries (domain ↔ infrastructure):**

| Port Protocol | Adapter(s) | External System |
|--------------|-----------|----------------|
| `AgentExecutionPort` | `CliBackend`, `SdkBackend` | Claude Code CLI / Agent SDK |
| `ModelDispatchPort` | `PalModelDispatch` | PAL MCP → Gemini, o4-mini, Codex |
| `MessagingPort` | `TelegramMessaging` | Telegram MCP (qpd-v) |
| `VideoProcessingPort` | `FFmpegProcessor` | FFmpeg binary |
| `VideoDownloadPort` | `YtDlpDownloader` | yt-dlp binary |
| `StateStorePort` | `FileStateStore` | Filesystem (run.md, sessions.json) |
| `FileDeliveryPort` | `GoogleDriveUploader` | Google Drive API |
| `KnowledgeBasePort` | `YamlKnowledgeBase` | crop-strategies.yaml |

### Requirements to Structure Mapping

**FR Category → Module Mapping:**

| FR Category | BMAD Workflow | Domain | Application | Infrastructure |
|------------|--------------|--------|-------------|---------------|
| Trigger & Elicitation (FR1-4) | `stage-01-router.md`, `agents/router/` | `QueueItem`, `RunState` | `queue_consumer` | `telegram_bot/`, `telegram_mcp_adapter` |
| Episode Analysis (FR5-9) | `stage-02-research.md`, `stage-03-transcript.md` | `VideoMetadata`, `AgentRequest` | `orchestrator` | `ytdlp_adapter`, `claude_cli_backend` |
| Camera & Video (FR10-16) | `stage-05-layout-detective.md`, `stage-06-ffmpeg-engineer.md` | `CropRegion`, `CameraLayout` | `orchestrator` | `ffmpeg_adapter`, `knowledge_base_adapter` |
| Content Generation (FR17-19) | `stage-04-content.md`, `agents/content-creator/` | `AgentRequest`, `AgentResult` | `orchestrator` | `claude_cli_backend` |
| Quality Assurance (FR20-24) | `qa/qa-gate-template.md`, `qa/gate-criteria/` | `QACritique`, `QADecision` | `reflection_loop`, `model_router` | `pal_mcp_adapter` |
| Delivery & Review (FR25-28) | `stage-08-delivery.md`, `agents/delivery/` | `ArtifactManifest` | `orchestrator` | `telegram_mcp_adapter`, `google_drive_adapter` |
| Revision & Feedback (FR29-34) | `revision-flows/*.md`, `agents/router/revision-interpretation.md` | `RevisionType` | `revision_router` | `telegram_mcp_adapter` |
| State & Recovery (FR35-39) | — (Python-managed, not BMAD steps) | `PipelineStage`, `RunState` | `state_machine`, `workspace_manager` | `file_state_store` |
| Operations (FR40-43) | — (Python-managed) | `PipelineEvent` | `event_bus` | `event_journal_writer`, `resource_monitor` |

### Data Flow

```
Telegram URL → polling_listener → url_validator → queue/inbox/
    → queue_consumer claims → workspace_manager creates run/
    → orchestrator drives FSM:
        Loads workflows/stages/stage-01-router.md + agents/router/agent.md
        → spawns: claude -p "{step_file + agent_def + context}" --mcp-config telegram.json
        → Claude Code executes BMAD step, writes artifacts to workspace
        → orchestrator collects artifacts, runs QA gate:
            Loads workflows/qa/gate-criteria/router-criteria.md + agents/qa/agent.md
            → spawns QA via PAL MCP (Gemini) with criteria + artifact
            → QA returns structured critique (Pydantic-validated)
        → FSM transitions: PASS → next stage, REWORK → re-run with feedback
        → repeat for all 8 stages
    → event_bus publishes to: journal_writer, checkpointer, telegram_notifier
    → on crash: systemd restarts → bootstrap reads run.md → resumes from checkpoint
```

### Integration Points

**Internal — Orchestrator ↔ BMAD Steps:**
- Orchestrator constructs prompt from: step file + agent definition + agent knowledge + prior artifacts + elicitation context
- Claude Code writes output artifacts to the per-run workspace
- Orchestrator reads artifacts from workspace after CLI process exits

**External — 8 Port Protocols:**
- All external tool access exclusively through Port Protocols
- Infrastructure adapters are the only code that imports third-party libraries
- Composition root (`bootstrap.py`) wires adapters to ports at startup

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
All technology choices work together without conflicts. Python 3.11+ supports `asyncio.TaskGroup`, `typing.Protocol`, and `tomllib` required by the architecture. Poetry manages the dependency graph. Pydantic v2, PyYAML, aiofiles, and python-telegram-bot are compatible on ARM aarch64. Claude Code CLI, FFmpeg, and yt-dlp are all available as standalone binaries on Raspberry Pi OS. systemd integration (watchdog, resource limits, environment files) is consistent with the daemon architecture. No version conflicts detected.

**Pattern Consistency:**
Implementation patterns fully support architectural decisions. Hexagonal Architecture import rules align with the 4-layer structure. Naming conventions (snake_case code, kebab-case config, dot-namespaced events) are consistent across all areas. Atomic write pattern supports the crash recovery requirement. QA critique schema (Pydantic-validated JSON) aligns with the reflection loop and multi-model routing decisions. Agent prompt contracts standardize the BMAD step file ↔ Python orchestrator interface.

**Structure Alignment:**
Project structure supports all architectural decisions. Two-layer separation (BMAD Workflow + Python Application) is cleanly represented in directory structure. Hexagonal layers are enforced by directory boundaries (`domain/` → `application/` → `infrastructure/` → `app/`). BMAD workflow files (stages, agents, QA gates, revision flows) are organized to match the FSM stage progression. Per-run workspace isolation supports checkpoint and crash recovery patterns.

### Requirements Coverage Validation

**Functional Requirements Coverage (43/43):**

| FR Category | FR Count | Architectural Support |
|------------|----------|----------------------|
| Trigger & Elicitation (FR1-4) | 4 | `telegram_bot/`, `queue_consumer`, `stage-01-router.md`, `agents/router/` |
| Episode Analysis (FR5-9) | 5 | `stage-02-research.md`, `stage-03-transcript.md`, `ytdlp_adapter`, `claude_cli_backend` |
| Camera & Video (FR10-16) | 7 | `stage-05-layout-detective.md`, `stage-06-ffmpeg-engineer.md`, `ffmpeg_adapter`, `knowledge_base_adapter` |
| Content Generation (FR17-19) | 3 | `stage-04-content.md`, `agents/content-creator/`, `claude_cli_backend` |
| Quality Assurance (FR20-24) | 5 | `qa/qa-gate-template.md`, `qa/gate-criteria/`, `reflection_loop`, `pal_mcp_adapter` |
| Delivery & Review (FR25-28) | 4 | `stage-08-delivery.md`, `agents/delivery/`, `telegram_mcp_adapter`, `google_drive_adapter` |
| Revision & Feedback (FR29-34) | 6 | `revision-flows/*.md`, `agents/router/revision-interpretation.md`, `revision_router` |
| State & Recovery (FR35-39) | 5 | `state_machine`, `workspace_manager`, `file_state_store`, `recovery_chain` |
| Operations (FR40-43) | 4 | `event_bus`, `event_journal_writer`, `resource_monitor`, `telegram_notifier` |

**Non-Functional Requirements Coverage (22/22):**

| NFR Category | Count | Architectural Support |
|-------------|-------|----------------------|
| Performance (P1-P6) | 6 | systemd resource limits, FFmpeg thread cap, tmpfs, async I/O |
| Reliability (R1-R6) | 6 | systemd restart, atomic writes, checkpoint/resume, watchdog heartbeat |
| Integration (I1-I6) | 6 | Telegram MCP adapter, 50MB threshold routing, PAL MCP lifecycle, Poetry deps |
| Security (S1-S4) | 4 | `.env` + `EnvironmentFile`, CHAT_ID whitelist, file permissions, no open ports |

### Implementation Readiness Validation

**Decision Completeness:**
All critical decisions documented with specific technology versions and configuration values. Implementation patterns provide concrete code examples (atomic write, event format, frontmatter schema, QA critique schema). Consistency rules are enforceable via tooling (mypy --strict, ruff, Pydantic validation, import linter).

**Structure Completeness:**
Complete directory structure with every file and directory defined. All 8 port protocols mapped to concrete adapters. All 8 pipeline stages mapped to BMAD step files and agent definitions. Integration points clearly specified (orchestrator ↔ CLI, CLI ↔ workspace, QA ↔ PAL MCP).

**Pattern Completeness:**
All 12 conflict points addressed across 5 categories. Naming conventions cover Python code, files, events. Process patterns cover atomic writes, checkpointing, error propagation, async boundaries. Communication patterns cover Telegram formatting and agent prompt contracts.

### Gap Analysis Results

**Critical Gaps:** 0

**Minor Gaps (3):**

| Gap | Impact | Mitigation |
|-----|--------|-----------|
| Agent SDK migration path not fully specified | Low — Phase 2 concern | `SdkBackend` adapter placeholder exists; `AgentExecutionPort` protocol ensures clean swap |
| Google Drive adapter auth flow not detailed | Low — fallback path only | Standard OAuth2 service account; details deferred to implementation story |
| Layout knowledge base schema not formalized | Low — self-expanding by design | Initial `crop-strategies.yaml` schema defined during implementation of Layout Detective agent |

### Validation Issues Addressed

**Poetry Integration (from Pedro's feedback):**
Added Poetry as the dependency management tool across the architecture:
- Starter Template: `poetry init` + `poetry add` initialization commands
- Project Structure: `poetry.lock` committed to git alongside `pyproject.toml`
- Infrastructure & Deployment: Poetry row added to decisions table
- Development Experience: Poetry referenced for virtual env and dependency management
- Scripts: `install.sh` updated to reference `poetry install`

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed (43 FRs, 22 NFRs mapped)
- [x] Scale and complexity assessed (medium, single-user POC)
- [x] Technical constraints identified (RPi ARM, 4GB RAM, shared Umbrel)
- [x] Cross-cutting concerns mapped (7 concerns)

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified (Python 3.11+, Poetry, Claude Code CLI, FFmpeg, yt-dlp)
- [x] Integration patterns defined (8 Port Protocols)
- [x] Performance considerations addressed (resource limits, tmpfs, thread caps)

**Implementation Patterns**

- [x] Naming conventions established (3 categories, 12 conflict points)
- [x] Structure patterns defined (Hexagonal layers, test organization, config organization)
- [x] Communication patterns specified (Telegram formatting, agent prompt contracts)
- [x] Process patterns documented (atomic writes, checkpoints, error propagation, async boundaries)

**Project Structure**

- [x] Complete directory structure defined (two-layer: BMAD Workflow + Python Application)
- [x] Component boundaries established (Hexagonal layers, port protocols)
- [x] Integration points mapped (orchestrator ↔ BMAD steps, 8 external ports)
- [x] Requirements to structure mapping complete (43 FRs + 22 NFRs → modules)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — all requirements covered, all decisions coherent, comprehensive patterns defined

**Key Strengths:**
- Two-layer architecture cleanly separates domain knowledge (BMAD markdown) from orchestration logic (Python)
- Hexagonal Architecture with 8 Port Protocols enables clean testing and future adapter swaps (CLI → SDK)
- Pre-validated patterns from 3 iterations of manual pipeline experience baked into agent knowledge files
- Complete BMAD workflow layer with stages, QA gates, revision flows, and agent definitions

**Areas for Future Enhancement:**
- Agent SDK migration (Phase 2) — adapter swap via `AgentExecutionPort`
- Multi-model QA escalation chain (Phase 2) — extend `ModelRouter`
- Video processing sub-agent decomposition (Phase 2) — split `stage-06-ffmpeg-engineer.md`

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect Hexagonal Architecture import rules — domain imports stdlib only
- Use Poetry for all dependency management — never `pip install` directly
- Refer to this document for all architectural questions

**First Implementation Priority:**
```bash
poetry init --name telegram-reels-pipeline --python "^3.11"
```
Scaffold the project structure, define domain types and Port Protocols, then build the FSM — following the 10-step implementation sequence from the Decision Impact Analysis.
