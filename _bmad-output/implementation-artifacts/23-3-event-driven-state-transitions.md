# Story 23.3: Event-Driven State Transitions

Status: ready-for-dev

## Story

As a System Operator,
I want every stage transition in the FSM to emit an immutable event to the database before proceeding,
So that if a crash occurs mid-stage, the exact last known state is safely recorded and the system never enters a "ghost state".

## Acceptance Criteria

1. **Given** the `PipelineOrchestrator` is processing a stage, **When** an agent successfully completes its task, **Then** a `pipeline.stage_completed` event must be written to MongoDB, **And** the `RunStateDocument` projection must be updated to reflect the new stage, **And** the pipeline must NOT proceed to the next stage until the database write is confirmed.

2. **Given** a stage fails with an error, **When** the orchestrator catches the exception, **Then** a `pipeline.error_occurred` event must be emitted with the error details in the payload, **And** the projection must reflect the error state.

3. **Given** a QA gate evaluates an agent output, **When** the result is PASS, REWORK, or FAIL, **Then** the corresponding event (`qa.gate_passed`, `qa.gate_rework`, `qa.gate_failed`) must be emitted with the critique payload.

4. **Given** the system crashes after an event is written but before the next stage starts, **When** the system restarts, **Then** the last event must accurately reflect the recoverable state, **And** the orchestrator must resume from that state.

## Tasks / Subtasks

- [ ] **Task 1: Create event emission service** (AC: #1, #2, #3)
  - [ ] Create `src/pipeline/application/services/pipeline_event_emitter_service.py`
  - [ ] `PipelineEventEmitterService` class with injected `EventStorePort` and `StateStorePort`
  - [ ] Methods:
    - `async emit_stage_entered(pipeline_run_id: str, stage_name: str) -> None`
    - `async emit_stage_completed(pipeline_run_id: str, stage_name: str, artifact_paths: tuple[str, ...]) -> None`
    - `async emit_qa_gate_result(pipeline_run_id: str, stage_name: str, qa_decision: str, critique_payload: Mapping) -> None`
    - `async emit_error_occurred(pipeline_run_id: str, stage_name: str, error_message: str) -> None`
    - `async emit_pipeline_paused(pipeline_run_id: str, reason: str) -> None`
    - `async emit_pipeline_resumed(pipeline_run_id: str) -> None`
  - [ ] Each method: creates `PipelineStateEvent`, appends to store, updates projection

- [ ] **Task 2: Integrate event emission into PipelineOrchestrator** (AC: #1, #2)
  - [ ] Modify `PipelineOrchestrator` to accept `PipelineEventEmitterService` via constructor injection
  - [ ] Before each stage: emit `stage_entered`
  - [ ] After successful stage: emit `stage_completed` with artifact metadata
  - [ ] On stage error: emit `error_occurred` with error details
  - [ ] CRITICAL: `await` the event write before proceeding to next stage (NFR-R1)

- [ ] **Task 3: Integrate event emission into ReflectionLoop** (AC: #3)
  - [ ] Modify `ReflectionLoop` to accept `PipelineEventEmitterService`
  - [ ] After each QA evaluation: emit appropriate QA event
  - [ ] Include full `QACritique` payload in event data (score, blockers, fixes)
  - [ ] Track attempt number in event payload

- [ ] **Task 4: Create crash recovery from event stream** (AC: #4)
  - [ ] Create `src/pipeline/application/use_cases/recover_pipeline_run_use_case.py`
  - [ ] `RecoverPipelineRunUseCase`:
    - Query event store for incomplete runs (status != `COMPLETED` or `FAILED`)
    - For each: replay events to determine last known good state
    - Resume orchestrator from that state
  - [ ] Must be called on application startup

- [ ] **Task 5: Create "write-ahead" confirmation pattern** (AC: #1, #4)
  - [ ] Ensure event is written and confirmed before FSM transitions
  - [ ] Pattern: `emit_event() → await confirmation → transition_state()`
  - [ ] If event write fails: do NOT transition, raise and let recovery chain handle it
  - [ ] Log write latency for NFR-P1 monitoring

- [ ] **Task 6: Write BDD feature file** (AC: #1, #2, #3, #4)
  - [ ] Create `tests/bdd/features/event_driven_transitions.feature`:
    - Scenario: Stage completion emits event before proceeding
    - Scenario: Stage failure emits error event
    - Scenario: QA gate emits evaluation event
    - Scenario: System recovers from crash using event stream
  - [ ] Step definitions with faked stores

- [ ] **Task 7: Write unit tests** (AC: #1, #2, #3)
  - [ ] `tests/unit/application/test_pipeline_event_emitter_service.py`
  - [ ] `tests/unit/application/test_recover_pipeline_run_use_case.py`
  - [ ] Verify event ordering, payload completeness, recovery accuracy

## Dev Notes

### Write-Ahead Event Pattern

This is the core reliability guarantee (NFR-R1). The pattern is:

```
1. Agent completes work → artifacts saved
2. Event emitted to MongoDB (WRITE-AHEAD)
3. Event write confirmed (await)
4. FSM transitions to next stage
5. Next agent begins
```

If the system crashes between steps 2 and 4, the event is already persisted. On restart, `RecoverPipelineRunUseCase` replays events and resumes from step 4.

### Event Payload Structure

Each event carries enough context to reconstruct the state:

```python
PipelineStateEvent(
    event_id="evt-abc123",
    pipeline_run_id="run-xyz789",
    event_type="pipeline.stage_completed",
    stage_name="transcript",
    payload_data=MappingProxyType({
        "artifact_paths": ("transcript_clean.txt", "moment-selection.json"),
        "duration_seconds": 45.2,
    }),
    created_at="2026-03-16T14:30:00Z",
)
```

### Integration with Existing EventBus

The existing in-process `EventBus` (Observer pattern) continues to work for in-process notifications (logging, Telegram updates). The new `PipelineEventEmitterService` adds **persistent** event storage. Both can coexist:
- `EventBus` → transient, in-process listeners
- `PipelineEventEmitterService` → persistent, MongoDB-backed

### References

- [Source: prd.md#Functional Requirements] — FR6 (immutable events), FR7 (state projection)
- [Source: prd.md#Non-Functional Requirements] — NFR-R1 (zero ghost states), NFR-R2 (graceful shutdown)
- [Source: epics.md#Story 2.3] — Event-Driven State Transitions
- [Source: brainstorming-session-2026-02-24.md#Theme 1] — The Document Carousel, Event Sourced State
