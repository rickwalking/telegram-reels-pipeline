---
date: 2026-03-18
topic: "Monorepo Integration — Dissolving telegram-reels-pipeline into three modules"
participants: [Pedro, Carson (Brainstorming Coach)]
status: draft
---

# Brainstorming Session: Monorepo Integration Architecture

## Problem Statement

Two separate systems exist that don't communicate:
- **Existing (Epics 1-21):** Working CLI-driven AI pipeline that generates Instagram Reels. Uses file-based state, direct filesystem I/O, Telegram-only trigger.
- **New (Epics 22-27):** FastAPI + MongoDB event sourcing + MCP tools + React SPA dashboard. Infrastructure is built but nothing flows through it.

All 151 pipeline runs in MongoDB are stuck at `pending` / `router` stage with only `pipeline.run_created` events — zero stage transitions, zero artifacts, zero real pipeline execution.

## Key Decisions

### 1. State Machine Stays, State Moves to MongoDB
- The FSM logic (domain/transitions.py, state_machine.py) is sacred — unchanged
- File-based state (run.md, events.log, sessions.json) → replaced by MongoDB event sourcing
- `FileStateStore` → `MongoStateStore` swap at composition root

### 2. Skills.md Pattern for Agent Invocation
- Following agentskills.io specification
- Each pipeline stage becomes a self-contained Skill
- SKILL.md < 500 lines, core instructions only
- `steps/` for progressive disclosure
- `references/` for domain knowledge loaded on-demand
- `scripts/` for reusable automation
- Agents use MCP tools to read context and save outputs

### 3. Fear: Breaking Existing Functionality
- Solution: **Strangler Fig Pattern** — wrap, don't rewrite
- `EventSourcedPipelineRunner` wraps existing `PipelineRunner`
- Existing agent execution path untouched in Phase 1
- Skills.md migration is Phase 2 (after dashboard is live with real data)

## Target Monorepo Structure

```
claude_docker/                          # Monorepo root
├── pipeline/                           # Core pipeline logic (Python)
│   ├── domain/                         # FSM, models, ports (stdlib only)
│   ├── application/                    # Use cases, orchestrator, event emitter
│   ├── infrastructure/                 # MongoDB, FFmpeg, yt-dlp adapters
│   └── presentation/                   # FastAPI REST + MCP tools
│
├── workflow-skills/                    # Agent Skills module (Markdown + Scripts)
│   ├── router/
│   │   ├── SKILL.md
│   │   ├── steps/
│   │   ├── references/
│   │   └── scripts/
│   ├── research/
│   ├── transcript/
│   ├── content-creator/
│   ├── layout-detective/
│   ├── ffmpeg-engineer/
│   ├── assembly/
│   └── delivery/
│
├── frontend/                           # React SPA dashboard
│   ├── src/core/                      # Shared component library
│   ├── src/app/                       # Dashboard pages
│   └── src/services/                  # API client, SSE
│
├── _bmad/                              # BMAD framework
├── _bmad-output/                       # Planning artifacts
└── CLAUDE.md                           # Root project rules
```

`telegram-reels-pipeline/` folder is dissolved — its contents distributed across the three modules.

## Migration Map

| Current Location | Moves To | What Changes |
|-----------------|----------|-------------|
| `src/pipeline/domain/` | `pipeline/domain/` | Nothing — domain is pure |
| `src/pipeline/application/` | `pipeline/application/` | Add EventSourcedPipelineRunner wrapper |
| `src/pipeline/infrastructure/` | `pipeline/infrastructure/` | Swap FileStateStore → MongoStateStore |
| `src/pipeline/presentation/` | `pipeline/presentation/` | Already FastAPI + MCP |
| `workflows/stages/*.md` | `workflow-skills/*/SKILL.md` | Restructure to Skills.md spec |
| `agents/*.md` | `workflow-skills/*/references/` | Merge into skill references |
| `workflows/qa/gate-criteria/` | `workflow-skills/*/references/` | QA criteria per skill |
| `scripts/*.py` | `workflow-skills/*/scripts/` | Reusable per-skill scripts |
| `config/*.yaml` | `pipeline/config/` | Pipeline-specific configuration |
| `systemd/` | `pipeline/systemd/` | Deployment config |
| `tests/` | `pipeline/tests/` | All existing tests preserved |

## Integration Strategy (Two Phases)

### Phase 1: "The Bridge" — State Migration + Event Sourcing
**Goal:** Existing pipeline runs exactly as before, but state goes to MongoDB and events stream to dashboard.

Changes:
1. `EventSourcedPipelineRunner` wraps existing `PipelineRunner` (zero changes to working code)
2. Every stage transition emits events via `PipelineEventEmitterService`
3. `app/bootstrap.py` swaps `FileStateStore` → `MongoStateStore`
4. Dashboard comes alive with real stage transitions, events, artifacts

NO changes to:
- Domain layer
- Agent execution (still `claude -p` via CLI)
- Agent definitions (still markdown files)
- FFmpeg/yt-dlp processing
- QA reflection loop logic

### Phase 2: "The Transformation" — Skills.md Agent Pattern
**Goal:** Agents become self-contained Skills loaded on-demand via MCP.

Changes:
1. Each stage's agent definition → SKILL.md following agentskills.io spec
2. Agent invocation: lightweight prompt loads skill, agent uses MCP tools for context
3. Agent outputs via MCP `save_stage_output` tool (already built)
4. Agent reads context via MCP `query_pipeline_status` tool (already built)

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Wrapper breaks agent execution | LOW | CRITICAL | Wrapper only adds events AROUND existing execution |
| MongoDB goes down during run | MEDIUM | HIGH | Circuit breaker: graceful degradation, log warning |
| Event emission adds latency | LOW | MEDIUM | Append-only writes, <50ms per event |
| Skills.md pattern incompatible with CLI | MEDIUM | HIGH | Prototype with ONE skill first |
| 668-line pipeline_runner.py too fragile | HIGH | HIGH | Wrapper pattern: DON'T modify it |

## Skills.md Specification (per agentskills.io)

Each pipeline stage skill follows:

```
workflow-skills/{stage}/
├── SKILL.md              # <500 lines, <5000 tokens
│   ├── Context Loading   # Which MCP tools to call for input
│   ├── Execution         # Step-by-step procedure
│   ├── Output Contract   # Which MCP tools to call for output
│   ├── Gotchas           # Non-obvious corrections
│   └── Validation        # QA rework loop
├── steps/                # Progressive disclosure
├── references/           # Domain knowledge, loaded on-demand
└── scripts/              # Reusable automation
```

## Proposed Epic Structure

- **Epic 28:** Monorepo Restructure (move files, update imports, new pyproject.toml — NO behavior changes)
- **Epic 29:** Event Sourcing Bridge (EventSourcedPipelineRunner wrapper, FileStateStore → MongoStateStore swap, SSE wiring)
- **Epic 30:** End-to-End Dashboard (real pipeline runs visible in React SPA, 3 successful runs required)
- **Epic 31:** Skills.md Migration (convert agents to Skills spec, MCP-driven invocation)
- **Epic 32:** Integration Testing & Hardening (full pipeline through new architecture, rollback tested)

## Consensus Validation (2026-03-18)

### Gemini-2.5-Pro (Advocate) — Score: 9/10
- Strangler Fig is correct lowest-risk pattern
- Hexagonal Architecture purpose-built for this swap
- Phase 1 delivers immediate observability value
- Skills.md + MCP strategically sound for long-term
- Two-phase approach de-risks complexity brilliantly

### Claude Opus (Skeptic Analysis — compensating for unavailable Codex)
Key risks identified:
1. PipelineRunner has implicit filesystem dependencies the wrapper can't intercept
2. Binary artifacts (videos) still need filesystem — dual-storage coordination needed
3. Solo developer scope is massive — added Phase 0 to isolate restructure risk
4. Agent prompt coupling is a fundamental behavior change, not just restructuring
5. Raspberry Pi MongoDB reliability under heavy FFmpeg load

### Additions from Consensus
- **Added Phase 0:** Monorepo restructure only (no behavior changes)
- **Added rollback capability:** FileStateStore stays as env-var-switchable fallback
- **Added Phase 2 entry criteria:** 3 successful end-to-end runs in dashboard before Skills.md
- **Added Phase 1.5 (merged into Epic 30):** Real agents run through wrapper, events stream to dashboard
