---
status: done
type: retrospective
scope: "Epics 1-6 (Full Project)"
completedAt: "2026-02-11"
consensus_models: ["gemini-2.5-pro (neutral)", "gemini-2.5-flash (devil's advocate)"]
---

# Project Retrospective: Epics 1-6

## Executive Summary

The project has **628 passing tests, 94% coverage, clean linting and type-checking**, and a well-designed hexagonal architecture across 6 completed epics. However, a post-implementation audit with multi-model consensus reveals that **the project is non-functional** — it is a robust architectural shell missing the entire content layer (agent definitions, workflow instructions, QA criteria) and the top-level wiring that would make it actually process videos.

**Consensus verdict (Gemini Pro + Flash, 10/10 confidence):** "The core engineering is done; the brains of the operation are completely absent."

---

## What Went Well

1. **Architecture** — Hexagonal architecture with strict layer boundaries, frozen dataclasses, exception chaining, and async I/O patterns are consistently applied across 54 source files.

2. **Test quality** — 628 unit tests with 94% coverage, AAA pattern, fakes over mocks for domain, proper async test support.

3. **Infrastructure adapters are real** — CliBackend (Claude subprocess), TelegramBotAdapter (python-telegram-bot), FFmpegAdapter (ffmpeg subprocess), YtDlpAdapter (yt-dlp with retries), GoogleDriveAdapter (OAuth2 upload) are all genuine implementations, not stubs.

4. **Reliability layer** — CrashRecoveryHandler, SystemdWatchdog, ResourceThrottler, RunCleaner are production-grade with symlink safety, /proc reading, sd_notify integration.

5. **Domain modeling** — 16 frozen dataclasses with validation, 5 enums, 9 port protocols, FSM transition table, proper NewType aliases.

---

## What Went Wrong

### Critical Gap 1: Empty Agent Definitions (8 files missing)

All 8 agent directories exist but contain **zero files**:
- `agents/router/agent.md` — empty
- `agents/research/agent.md` — empty
- `agents/transcript/agent.md` — empty
- `agents/content-creator/agent.md` — empty
- `agents/layout-detective/agent.md` — empty
- `agents/ffmpeg-engineer/agent.md` — empty
- `agents/qa/agent.md` — empty
- `agents/delivery/agent.md` — empty

**Impact:** `PromptBuilder.build()` calls `request.agent_definition.read_text()` which will crash with `FileNotFoundError`. The agents ARE the core intelligence of the system — they define what Claude does at each stage.

### Critical Gap 2: Empty Workflow Stage Files (8 files missing)

The `workflows/stages/` directory is empty:
- `stage-01-router.md` through `stage-08-delivery.md` — all missing

**Impact:** `PipelineRunner._build_request()` constructs paths to these files. `PromptBuilder` reads them to build the agent prompt. Without them, no stage can execute.

### Critical Gap 3: Empty QA Gate Criteria (7 files missing)

The `workflows/qa/gate-criteria/` directory is empty:
- `router-criteria.md`, `research-criteria.md`, `transcript-criteria.md`, `content-criteria.md`, `layout-criteria.md`, `ffmpeg-criteria.md`, `assembly-criteria.md` — all missing

**Impact:** `PipelineRunner._load_gate_criteria()` returns empty string, so the QA ReflectionLoop evaluates against no criteria — making QA gates meaningless.

### Critical Gap 4: Pipeline Never Executes (main.py stub)

`main.py` lines 55-58 contain:
```python
# Pipeline execution would happen here
# For now, just log the URL
```

`PipelineRunner` is:
- Fully implemented (245 lines, 8-stage orchestration)
- Fully tested (unit tests pass)
- Never instantiated in `bootstrap.py`
- Never called in `main.py`
- Not a field on the `Orchestrator` dataclass

Queue items are claimed and marked "completed" without any processing.

### Critical Gap 5: Missing Supporting Content Files

Per the PRD, each agent needs additional knowledge files:
- `agents/router/elicitation-flow.md`
- `agents/router/revision-interpretation.md`
- `agents/research/metadata-extraction.md`
- `agents/transcript/moment-selection-criteria.md`
- `agents/content-creator/description-style-guide.md`
- `agents/content-creator/hashtag-strategy.md`
- `agents/layout-detective/frame-analysis.md`
- `agents/layout-detective/escalation-protocol.md`
- `agents/ffmpeg-engineer/crop-playbook.md`
- `agents/ffmpeg-engineer/encoding-params.md`
- `agents/delivery/message-templates.md`

### Critical Gap 6: No .env Configuration

No `.env` file exists. Without it:
- No Telegram token → bot disabled
- No Anthropic API key → Claude CLI won't work
- No Google Drive credentials → large file upload fails

### Critical Gap 7: No Integration Tests

Only 1 integration test exists (`test_file_state_store.py`). Missing:
- End-to-end pipeline orchestration test (mocked external services)
- Agent execution integration test
- Full happy-path workflow test
- Recovery/resume integration test

### Critical Gap 8: Empty Revision Flows

`workflows/revision-flows/` is empty. The revision handler code references these but they don't exist.

---

## Consensus Analysis

### Points of Agreement (both models)

1. **All 8 gaps are real and critical** — even the devil's advocate (Flash) found no defensible counter-arguments
2. **Project delivers zero user value** in current state
3. **Architecture is sound** — the hexagonal design, port protocols, and async patterns are production-quality
4. **Gaps are content-based, not technical** — the remaining work is primarily prompt engineering and domain knowledge
5. **Hand-crafted agent definitions recommended** over AI-generated for v1.0 predictability
6. **Integration tests are mandatory** before any production deployment
7. **MVP approach recommended** — start with fewer stages to validate before full 8-stage pipeline

### Points of Disagreement

None. Both models reached full consensus that all gaps require resolution. Flash suggested a hybrid approach (hand-craft core, AI-assist variations) which Pro did not explicitly address, but this is a nuance rather than a disagreement.

---

## Recommended New Epics

### Epic 7: Agent Definitions & Workflow Content (HIGH — largest remaining work)

| Story | Title | Scope |
|-------|-------|-------|
| 7.1 | Router Agent definition + elicitation flow | `agents/router/agent.md`, elicitation-flow.md, revision-interpretation.md |
| 7.2 | Research Agent definition + metadata extraction | `agents/research/agent.md`, metadata-extraction.md |
| 7.3 | Transcript Agent definition + moment selection criteria | `agents/transcript/agent.md`, moment-selection-criteria.md |
| 7.4 | Content Creator Agent definition + style guides | `agents/content-creator/agent.md`, description-style-guide.md, hashtag-strategy.md |
| 7.5 | Layout Detective Agent definition + escalation protocol | `agents/layout-detective/agent.md`, frame-analysis.md, escalation-protocol.md |
| 7.6 | FFmpeg Engineer Agent definition + crop playbook | `agents/ffmpeg-engineer/agent.md`, crop-playbook.md, encoding-params.md |
| 7.7 | Assembly Agent definition | `agents/qa/agent.md` |
| 7.8 | Delivery Agent definition + message templates | `agents/delivery/agent.md`, message-templates.md |

### Epic 8: Workflow Stage Files & QA Gate Criteria

| Story | Title | Scope |
|-------|-------|-------|
| 8.1 | Stage workflow files (8 files) | `workflows/stages/stage-01-router.md` through `stage-08-delivery.md` |
| 8.2 | QA gate criteria files (7 files) | `workflows/qa/gate-criteria/*-criteria.md` |
| 8.3 | Revision flow definitions | `workflows/revision-flows/` |

### Epic 9: Pipeline Wiring & Integration

| Story | Title | Scope |
|-------|-------|-------|
| 9.1 | Wire PipelineRunner into Orchestrator + bootstrap | Add to dataclass, instantiate in `create_orchestrator()` |
| 9.2 | Connect main.py processing loop to PipelineRunner | Replace stub with `await pipeline_runner.run(item, workspace)` |
| 9.3 | .env template + configuration documentation | `.env.example` with all required variables |
| 9.4 | Mocked end-to-end integration tests | Full pipeline orchestration with fake adapters |
| 9.5 | Smoke test with real services | Single-URL happy path against real YouTube/Telegram/Claude |

---

## Priority Ordering

1. **Epic 9.1-9.2** (wire PipelineRunner) — low complexity, unblocks everything
2. **Epic 7** (agent definitions) — highest effort, core intelligence
3. **Epic 8** (workflow/gate files) — medium effort, enables QA loop
4. **Epic 9.3** (.env configuration) — required for real execution
5. **Epic 9.4-9.5** (integration tests) — validates everything works together

---

## Metrics

| Metric | Value |
|--------|-------|
| Epics completed | 6/6 (infrastructure only) |
| Stories completed | 30/30 |
| Tests passing | 628 |
| Coverage | 94.05% |
| Source files | 54 |
| Missing content files | ~30 (.md agent/stage/gate definitions) |
| Functional pipeline runs possible | 0 |
| Estimated remaining work | Epics 7-9 (3 new epics, ~16 stories) |
