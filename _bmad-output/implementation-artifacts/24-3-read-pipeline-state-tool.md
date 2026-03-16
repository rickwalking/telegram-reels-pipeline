# Story 24.3: Read Pipeline State Tool

Status: ready-for-dev

## Story

As an AI Agent,
I want to query the current state and prior completed stage artifacts of a pipeline run,
So that I understand my context and requirements for the current task.

## Acceptance Criteria

1. **Given** a running FastMCP server, **When** the agent calls `query_pipeline_status(pipeline_run_id)`, **Then** the tool must fetch the current `RunStateProjection` via the `StateStorePort`, **And** return a JSON response with the current stage, completed stages, and escalation status.

2. **Given** a pipeline run with completed stages, **When** the agent calls `get_stage_artifacts(pipeline_run_id, stage_name)`, **Then** the tool must return the artifact metadata from the event store for that specific stage.

3. **Given** a non-existent `pipeline_run_id`, **When** the agent queries, **Then** the tool must return a structured error response indicating the run was not found.

4. **Given** all tools, **When** Claude discovers them, **Then** each tool must have a comprehensive docstring describing its purpose, parameters, and return format.

## Existing Code Audit

- `presentation/mcp/server.py` has a stub `query_pipeline_status(run_id: str)` tool that returns a hardcoded string `"Run {run_id} is currently active."` — no real implementation, no use case invocation, no error handling.
- No `get_stage_artifacts`, `list_available_stages`, or `get_qa_history` tools exist.
- No application use cases exist for reading pipeline state via MCP.

## Tasks / Subtasks

- [ ] **Task 1: Create query pipeline status tool** (AC: #1, #3) [REWRITE of existing stub]
  - [ ] Create `src/pipeline/presentation/tools/query_pipeline_status_tool.py`
  - [ ] Register tool with FastMCP: `@mcp_server.tool()`
  - [ ] Parameters: `pipeline_run_id: str`
  - [ ] Calls `GetPipelineRunDetailUseCase`
  - [ ] Returns formatted JSON with: `pipeline_run_id`, `current_stage`, `execution_status`, `completed_stages`, `escalation_status`, `current_attempt_count`
  - [ ] On not found: return error response (not exception)

- [ ] **Task 2: Create get stage artifacts tool** (AC: #2)
  - [ ] Create `src/pipeline/presentation/tools/get_stage_artifacts_tool.py`
  - [ ] Register tool with FastMCP
  - [ ] Parameters: `pipeline_run_id: str`, `stage_name: str`
  - [ ] Create `GetStageArtifactsUseCase` in application layer
  - [ ] Queries event store for `stage_completed` events matching the stage
  - [ ] Returns artifact metadata (paths, timestamps, QA scores)

- [ ] **Task 3: Create list available stages tool** (AC: #4)
  - [ ] Create `src/pipeline/presentation/tools/list_available_stages_tool.py`
  - [ ] Returns the list of all pipeline stages with descriptions
  - [ ] Helps agents understand the pipeline flow
  - [ ] Pure data, no database query needed

- [ ] **Task 4: Create get QA history tool** (AC: #2)
  - [ ] Create `src/pipeline/presentation/tools/get_qa_history_tool.py`
  - [ ] Parameters: `pipeline_run_id: str`, `stage_name: str`
  - [ ] Queries event store for QA events (pass/rework/fail) for the stage
  - [ ] Returns attempt history with scores and feedback
  - [ ] Helps agents understand what went wrong in prior attempts

- [ ] **Task 5: Create application use cases** (AC: #1, #2)
  - [ ] `GetPipelineRunDetailUseCase` (if not already from 22-4)
  - [ ] `GetStageArtifactsUseCase` — queries events for stage artifacts
  - [ ] `GetQaHistoryUseCase` — queries events for QA attempts
  - [ ] All use cases inject `EventStorePort` and/or `StateStorePort`

- [ ] **Task 6: Write unit tests** (AC: #1, #2, #3)
  - [ ] `tests/unit/presentation/test_query_pipeline_status_tool.py`
  - [ ] `tests/unit/presentation/test_get_stage_artifacts_tool.py`
  - [ ] `tests/unit/presentation/test_get_qa_history_tool.py`
  - [ ] Test with faked stores
  - [ ] Verify error handling for non-existent runs

- [ ] **Task 7: Write integration tests with MCP client** (AC: #1, #4)
  - [ ] `tests/integration/test_mcp_read_tools.py`
  - [ ] Use official MCP test client to invoke tools
  - [ ] Verify tool discovery returns proper schemas
  - [ ] Verify tool docstrings are present and descriptive

## Dev Notes

### Tool Design for LLM Consumption

Tools must be designed for Claude to use effectively:
- **Descriptive docstrings** — Claude reads these to decide which tool to call
- **Simple parameter types** — prefer `str` over complex objects
- **JSON string responses** — Claude parses these naturally
- **Error responses in-band** — return errors as structured JSON, not exceptions

### Agent Context Building Pattern

A typical agent workflow uses these tools in sequence:
1. `query_pipeline_status(run_id)` — understand where we are
2. `get_stage_artifacts(run_id, "previous_stage")` — understand what's been done
3. `get_qa_history(run_id, "current_stage")` — understand prior attempts (if rework)
4. Agent does its work
5. `save_stage_output(run_id, ...)` — save results (Story 24-4)

### NFR Compliance

- NFR-I1: Agents have no direct file system I/O for state — all state access through MCP tools
- NFR-P1: Tool response time <500ms — tests should assert timing

### References

- [Source: prd.md#AI Agent Interaction] — FR9 (read pipeline state via MCP tools)
- [Source: epics.md#Story 3.3] — Read Pipeline State Tool
- [Source: architecture.md#Agent Prompt Contracts] — Context bundle per agent
- [Source: CLAUDE.md#Hexagonal Tool-Adapter] — Agents interact via MCP tools
