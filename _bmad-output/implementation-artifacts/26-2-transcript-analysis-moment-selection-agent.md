# Story 26.2: Transcript Analysis & Moment Selection Agent

Status: ready-for-dev

## Story

As an AI Agent,
I want to analyze the downloaded transcript to find the most engaging narrative moments,
So that the Reel has high-quality content focused on the requested topic.

## Acceptance Criteria

1. **Given** a downloaded transcript, **When** the Claude AI Agent processes the text, **Then** it must return a JSON payload with selected timestamps, narrative roles, and reasoning, **And** the payload must be validated against `TranscriptOutputDTO`.

2. **Given** the validated output, **When** it is saved, **Then** a `stage_completed` event must be committed to the Event Store with the moment selection data.

3. **Given** the existing Transcript Agent workflow, **When** integrating into the new architecture, **Then** the agent must read prior stage artifacts via MCP tools (not filesystem), **And** save outputs via MCP tools (not filesystem).

4. **Given** multi-moment mode, **When** the agent selects moments, **Then** it must include a `moments` array with narrative roles following `NARRATIVE_ROLE_ORDER`.

## Tasks / Subtasks

- [ ] **Task 1: Create transcript analysis use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/analyze_transcript_use_case.py`
  - [ ] `AnalyzeTranscriptUseCase` with injected: `AgentExecutionPort`, `EventStorePort`, `PipelineEventEmitterService`
  - [ ] Steps:
    1. Load prior stage artifacts (research output, transcript text) from event store
    2. Build agent prompt with context
    3. Execute agent via `AgentExecutionPort`
    4. Validate agent output via `TranscriptOutputDTO`
    5. Map to domain entity (Double-Gate)
    6. Emit `stage_completed` event
  - [ ] Support both single-moment and multi-moment selection

- [ ] **Task 2: Update TranscriptOutputDTO** (AC: #1, #4)
  - [ ] Ensure `presentation/dtos/transcript_output_dto.py` validates:
    - `moment_start_seconds: float` (positive, < video duration)
    - `moment_end_seconds: float` (> start)
    - `selected_quote: str` (non-empty)
    - `narrative_role: str` (from allowed set)
    - `selection_reasoning: str`
    - For multi-moment: `moments: list[MomentSelectionItemDTO]`
  - [ ] Validator: `end_seconds > start_seconds`
  - [ ] Validator: moment duration within acceptable range

- [ ] **Task 3: Create agent context builder** (AC: #3)
  - [ ] Create `src/pipeline/application/services/agent_context_builder_service.py`
  - [ ] Builds the prompt bundle for the transcript agent:
    - Stage requirements (from workflow files)
    - Prior artifacts (research output, transcript text — from event store)
    - Elicitation context (topic, style preferences — from router output)
    - Attempt history (QA feedback — from event store if rework)
  - [ ] All context fetched via ports, not filesystem

- [ ] **Task 4: Write BDD feature file** (AC: #1, #2, #3)
  - [ ] Create `tests/bdd/features/analyze_transcript.feature`:
    - Scenario: Agent selects a valid single moment
    - Scenario: Agent selects multiple moments for extended narrative
    - Scenario: Agent output fails DTO validation
  - [ ] Step definitions with faked ports and agent execution

- [ ] **Task 5: Write unit tests** (AC: #1, #2, #4)
  - [ ] `tests/unit/application/test_analyze_transcript_use_case.py`
  - [ ] `tests/unit/presentation/test_transcript_output_dto.py`
  - [ ] Test: valid single-moment output
  - [ ] Test: valid multi-moment output with narrative roles
  - [ ] Test: invalid timestamps → validation error

## Dev Notes

### Agent Interaction Pattern (New Architecture)

```
Orchestrator triggers AnalyzeTranscriptUseCase
    ↓
Use Case fetches context from EventStore (prior artifacts)
    ↓
Use Case builds prompt via AgentContextBuilderService
    ↓
Use Case calls AgentExecutionPort.execute(prompt)
    ↓
Agent runs (Claude Code CLI or Agent SDK)
    ↓
Agent calls MCP tool: save_stage_output(run_id, "transcript", json_payload)
    ↓
MCP tool validates via TranscriptOutputDTO (Gate 1)
    ↓
Mapper creates domain entity (Gate 2: __post_init__)
    ↓
Event stored in MongoDB
```

### Migration from Filesystem to Event Store

The key architectural change: agents no longer read from/write to workspace files directly. Instead:
- **Read**: Agent calls `query_pipeline_status` and `get_stage_artifacts` MCP tools
- **Write**: Agent calls `save_stage_output` MCP tool
- The `FileStoragePort` is only used for binary media (video files)

### References

- [Source: prd.md#Core Processing] — FR17 (transcript analysis)
- [Source: epics.md#Story 5.2] — Transcript Analysis & Moment Selection Agent
- [Source: CLAUDE.md#Pipeline Stages] — Stage 3: Transcript agent, moment-selection.json
- [Source: architecture.md#Agent Prompt Contracts] — Standardized input bundle per agent
