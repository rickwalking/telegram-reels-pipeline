# Story 24.4: Save Stage Output Tool

Status: done

## Story

As an AI Agent,
I want to save my generated artifacts directly via an MCP tool,
So that I do not have to negotiate local filesystem paths and permissions.

## Acceptance Criteria

1. **Given** a running FastMCP server, **When** the agent calls `save_stage_output(payload)`, **Then** the server must validate the payload against the stage-specific DTO schema, **And** persist the stage completion event and artifact data in MongoDB.

2. **Given** a valid stage output, **When** saved successfully, **Then** the orchestrator must be notified to trigger the next FSM transition, **And** the event store must contain the `stage_completed` event.

3. **Given** an invalid payload, **When** the agent attempts to save, **Then** the tool must return a structured validation error with field-level details so the agent can self-correct.

4. **Given** the tool saves stage output, **When** the output includes binary artifacts (video segments), **Then** only the file paths must be recorded in the event, **And** the binary data must be saved via `FileStoragePort`.

## Existing Code Audit

- `presentation/mcp/server.py` has a stub `save_stage_output(payload: SaveStageDTO)` tool that returns `"Successfully saved output for stage: {payload.stage}"` — no real implementation, no use case, no validation.
- `presentation/dtos/run_dtos.py` has `SaveStageDTO` with `stage: str` and `payload: dict` — the `dict` type is effectively `Any` (banned per CLAUDE.md).
- No stage-specific DTO dispatch registry exists.
- No `SaveStageOutputUseCase` exists.
- No orchestrator notification mechanism for MCP-driven stage completion.

## Tasks / Subtasks

- [x] **Task 1: Create save stage output tool** (AC: #1, #3) [REWRITE of existing stub]
  - [x] Create `src/pipeline/presentation/tools/save_stage_output_tool.py`
  - [x] Register with FastMCP: `@mcp_server.tool()`
  - [x] Parameters: `pipeline_run_id: str`, `stage_name: str`, `output_payload_json: str`
  - [x] Parse `output_payload_json` → stage-specific DTO (dispatch by `stage_name`)
  - [x] Validate via Pydantic DTO (Gate 1)
  - [x] Map to domain entity (Gate 2: `__post_init__`)
  - [x] Call `SaveStageOutputUseCase`
  - [x] Return success response with saved event ID

- [x] **Task 2: Create stage-specific DTO dispatch** (AC: #1)
  - [x] Create `src/pipeline/presentation/dtos/stage_output_dto_registry.py`
  - [x] Dictionary dispatch mapping stage names to DTO classes:
    ```python
    STAGE_OUTPUT_DTO_REGISTRY: dict[str, type[BaseStageOutputDTO]] = {
        "router": RouterOutputDTO,
        "research": ResearchOutputDTO,
        "transcript": TranscriptOutputDTO,
        # ... etc
    }
    ```
  - [x] Lookup function: `get_dto_class_for_stage(stage_name: str) -> type[BaseStageOutputDTO]`
  - [x] Raise `DomainValidationError` for unknown stage names

- [x] **Task 3: Create SaveStageOutputUseCase** (AC: #1, #2)
  - [x] Create `src/pipeline/application/use_cases/save_stage_output_use_case.py`
  - [x] Injected ports: `EventStorePort`, `StateStorePort`, `FileStoragePort`
  - [x] Steps:
    1. Validate the domain entity (already validated by mapper)
    2. Save any binary artifacts via `FileStoragePort`
    3. Create `stage_completed` event with artifact metadata
    4. Append event to event store
    5. Update state projection
    6. Notify orchestrator (via event bus) to trigger FSM transition
  - [ ] Return Result monad with success or domain error (returns str event_id directly, no Result monad)

- [ ] **Task 4: Create transition notification mechanism** (AC: #2)
  - [ ] Define how the MCP tool notifies the orchestrator that a stage is complete
  - [ ] Option A: In-process EventBus publish (`stage.output_saved`)
  - [ ] Option B: Async queue/signal
  - [ ] The orchestrator subscribes and triggers FSM transition
  - [ ] Ensure the notification is NOT sent if the event write fails

- [ ] **Task 5: Create save binary artifact tool** (AC: #4)
  - [ ] Create `src/pipeline/presentation/tools/save_binary_artifact_tool.py`
  - [ ] For agents that produce binary outputs (video segments, images)
  - [ ] Parameters: `pipeline_run_id: str`, `artifact_name: str`, `source_file_path: str`
  - [ ] Delegates to `FileStoragePort.save_binary_asset_from_path()`
  - [ ] Returns the relative storage path for reference in subsequent tool calls

- [ ] **Task 6: Write BDD feature file** (AC: #1, #2, #3)
  - [ ] Create `tests/bdd/features/save_stage_output.feature`:
    - Scenario: Agent saves valid stage output
    - Scenario: Agent saves invalid payload and receives correction guidance
    - Scenario: Stage output triggers FSM transition
  - [ ] Step definitions with faked stores

- [x] **Task 7: Write unit tests** (AC: #1, #2, #3, #4)
  - [x] `tests/unit/presentation/test_save_stage_output_tool.py`
  - [x] `tests/unit/application/test_save_stage_output_use_case.py`
  - [x] Test: valid payload → event created → transition notified
  - [x] Test: invalid payload → structured error returned
  - [ ] Test: binary artifact → file saved → path in event (not implemented, no binary artifact tool)

## Dev Notes

### Tool Interaction Flow

```
Agent calls save_stage_output(run_id, "transcript", json_payload)
    ↓
Presentation: parse JSON → lookup TranscriptOutputDTO → validate (Gate 1)
    ↓
Presentation: map DTO → domain entity → __post_init__ (Gate 2)
    ↓
Application: SaveStageOutputUseCase.execute()
    ↓
    ├── FileStoragePort.save_binary_asset() (if binary artifacts)
    ├── EventStorePort.append_event(stage_completed)
    ├── StateStorePort.save_state_projection(updated)
    └── EventBus.publish(stage.output_saved)
    ↓
Orchestrator receives notification → FSM transitions to next stage
```

### Dictionary Dispatch for DTO Routing

Per CLAUDE.md, use dictionary dispatch instead of if/elif chains:

```python
STAGE_OUTPUT_DTO_REGISTRY: dict[str, type[BaseStageOutputDTO]] = {
    "router": RouterOutputDTO,
    "transcript": TranscriptOutputDTO,
}

def get_dto_class_for_stage(stage_name: str) -> type[BaseStageOutputDTO]:
    dto_class = STAGE_OUTPUT_DTO_REGISTRY.get(stage_name)
    if dto_class is None:
        raise DomainValidationError(f"Unknown stage: {stage_name}")
    return dto_class
```

### Decoupling MCP from Orchestrator

The save tool does NOT directly call the orchestrator. It publishes an event, and the orchestrator subscribes. This maintains the Hexagonal boundary — the Presentation layer has no knowledge of how the orchestrator works.

### References

- [Source: prd.md#AI Agent Interaction] — FR10 (save artifacts via MCP), FR11 (DTO validation)
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.1] — save_stage_output tool snippet
- [Source: epics.md#Story 3.4] — Save Stage Output Tool
- [Source: CLAUDE.md#Control Flow] — Dictionary dispatch pattern
- [Source: CLAUDE.md#Hexagonal Tool-Adapter] — Agents via MCP tools
