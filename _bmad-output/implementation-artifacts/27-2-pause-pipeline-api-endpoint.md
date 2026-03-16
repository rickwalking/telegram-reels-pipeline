# Story 27.2: Pause Pipeline API Endpoint

Status: ready-for-dev

## Story

As a System Operator,
I want to explicitly pause a running pipeline via the REST API,
So that I can intervene if I notice the agent making a mistake in the live dashboard.

## Acceptance Criteria

1. **Given** an active pipeline run, **When** a `POST /api/runs/{pipeline_run_id}/pause` request is made, **Then** the Orchestrator must finish its current atomic operation (graceful pause), **And** the `RunState` must be updated to `PAUSED` status, **And** a `pipeline.paused` event must be emitted.

2. **Given** a paused pipeline, **When** a second pause request is made, **Then** the API must return 409 Conflict indicating the run is already paused.

3. **Given** a completed or failed pipeline, **When** a pause request is made, **Then** the API must return 400 Bad Request indicating the run is not in a pausable state.

4. **Given** the SSE stream is active, **When** the pipeline is paused, **Then** the UI must immediately reflect the paused state with a visual indicator.

## Tasks / Subtasks

- [ ] **Task 1: Create pause API endpoint** (AC: #1, #2, #3)
  - [ ] Add `POST /api/runs/{pipeline_run_id}/pause` to `pipeline_runs_router.py`
  - [ ] Request body: optional `reason: str`
  - [ ] Validate run exists and is in a pausable state (IN_PROGRESS)
  - [ ] Return 200 on success, 409 if already paused, 400 if not pausable, 404 if not found

- [ ] **Task 2: Create pause use case** (AC: #1)
  - [ ] Create `src/pipeline/application/use_cases/pause_pipeline_run_use_case.py`
  - [ ] `PausePipelineRunUseCase` with injected: `EventStorePort`, `StateStorePort`, `SseBroadcastPort`
  - [ ] Steps:
    1. Load current run state
    2. Validate it's pausable (IN_PROGRESS)
    3. Signal orchestrator to pause after current atomic operation
    4. Emit `pipeline.paused` event with reason
    5. Update projection: `execution_status = PAUSED`, `escalation_status = MANUAL_PAUSE`
    6. Broadcast via SSE

- [ ] **Task 3: Implement graceful pause signal** (AC: #1)
  - [ ] Create `PauseSignal` mechanism in orchestrator:
    - `request_pause(pipeline_run_id: str) -> None`
    - Orchestrator checks for pause signal between stages (not mid-stage)
    - If signal found: stop processing, emit paused event
  - [ ] Use `asyncio.Event` or shared state for signal delivery
  - [ ] CRITICAL: never interrupt mid-agent-execution (would corrupt state)

- [ ] **Task 4: Add pause button to React UI** (AC: #4)
  - [ ] Add "Pause Pipeline" button to `RunDetailPage.tsx`
  - [ ] Only visible when run status is `IN_PROGRESS`
  - [ ] Confirmation dialog: "Are you sure you want to pause this run?"
  - [ ] After pause: button changes to "Resume" (Story 27-3)
  - [ ] SSE updates UI state immediately

- [ ] **Task 5: Write BDD feature file** (AC: #1, #2, #3)
  - [ ] Create `tests/bdd/features/pause_pipeline_run.feature`:
    - Scenario: Pause active pipeline run
    - Scenario: Attempt to pause already-paused run
    - Scenario: Attempt to pause completed run
  - [ ] Step definitions with faked stores

- [ ] **Task 6: Write unit tests** (AC: #1, #2, #3)
  - [ ] `tests/unit/application/test_pause_pipeline_run_use_case.py`
  - [ ] `tests/unit/presentation/test_pause_endpoint.py`
  - [ ] Test: valid pause → event emitted, status updated
  - [ ] Test: already paused → 409 returned
  - [ ] Test: not pausable → 400 returned

## Dev Notes

### Graceful Pause Pattern

The orchestrator runs stages sequentially. The pause signal is checked at stage boundaries:

```
Stage N completes
  ↓
Check for pause signal ← pause request sets this flag
  ↓ (if paused)
Emit pipeline.paused event → stop processing
  ↓ (if not paused)
Proceed to Stage N+1
```

This ensures:
- No agent is interrupted mid-execution
- The last completed stage is fully saved (event + projection)
- The resume point is clean and deterministic

### Idempotency

The pause endpoint is designed to be safe for retries:
- If already paused: return 409 (no state change)
- If already completed/failed: return 400 (no state change)
- The event store prevents duplicate pause events

### References

- [Source: prd.md#Functional Requirements] — FR4 (pause for human approval)
- [Source: prd.md#User Success] — Interactive Intervention
- [Source: epics.md#Story 6.2] — Pause Pipeline API Endpoint
