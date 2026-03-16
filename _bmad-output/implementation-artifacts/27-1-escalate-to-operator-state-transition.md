# Story 27.1: Escalate to Operator State Transition

Status: ready-for-dev

## Story

As a System Operator,
I want the FSM to transition to an "Escalation" state when it encounters a critical error or unknown layout,
So that the system does not crash or generate garbage outputs without human oversight.

## Acceptance Criteria

1. **Given** the FSM is processing a stage, **When** a predefined escalation condition is met (e.g., `LayoutUnknown`, QA exhausted), **Then** the `PipelineOrchestrator` must set the run's escalation status to active, **And** pause further automated transitions, **And** commit the paused state to MongoDB via events.

2. **Given** an escalation event is emitted, **When** the operator views the dashboard, **Then** the run must show a prominent "Needs Attention" indicator, **And** the escalation reason and context must be visible.

3. **Given** the SSE stream is active, **When** escalation occurs, **Then** the UI must receive the escalation event in real-time.

4. **Given** the Telegram bot is connected, **When** escalation occurs, **Then** a notification must be sent via the `MessagingPort` with context (screenshot, error details, suggested actions).

## Tasks / Subtasks

- [ ] **Task 1: Define escalation event types** (AC: #1)
  - [ ] Add event types to domain constants:
    - `ESCALATION_LAYOUT_UNKNOWN = "escalation.layout_unknown"`
    - `ESCALATION_QA_EXHAUSTED = "escalation.qa_exhausted"`
    - `ESCALATION_AGENT_ERROR = "escalation.agent_error"`
    - `ESCALATION_MANUAL_PAUSE = "escalation.manual_pause"`
  - [ ] Each escalation type carries specific payload (reason, context, suggested actions)

- [ ] **Task 2: Create escalation use case** (AC: #1)
  - [ ] Create `src/pipeline/application/use_cases/escalate_pipeline_run_use_case.py`
  - [ ] `EscalatePipelineRunUseCase` with injected: `EventStorePort`, `StateStorePort`, `SseBroadcastPort`, `MessagingPort`
  - [ ] Steps:
    1. Emit escalation event with full context to event store
    2. Update run projection: `execution_status = PAUSED`, `escalation_status = <reason>`
    3. Broadcast escalation event via SSE
    4. Send Telegram notification with context

- [ ] **Task 3: Integrate escalation triggers into orchestrator** (AC: #1)
  - [ ] When `UnknownLayoutError` is caught → call `EscalatePipelineRunUseCase`
  - [ ] When QA best-of-three all fail below threshold → call escalation
  - [ ] When unrecoverable agent error after recovery chain exhaustion → call escalation
  - [ ] After escalation: orchestrator stops processing (run is paused)

- [ ] **Task 4: Create escalation notification for Telegram** (AC: #4)
  - [ ] Format escalation message with:
    - Run ID and YouTube URL
    - Failed stage and attempt count
    - Escalation reason
    - Suggested actions (A/B/C options)
    - Screenshot of last frame (if layout issue)
  - [ ] Send via `MessagingPort.notify_user()`

- [ ] **Task 5: Create escalation indicator for React SPA** (AC: #2, #3)
  - [ ] Create `frontend/src/components/EscalationBanner.tsx`
  - [ ] Prominent banner: red background, pulsing attention indicator
  - [ ] Shows: escalation reason, time paused, action buttons
  - [ ] SSE hook updates banner in real-time when escalation event received

- [ ] **Task 6: Write BDD feature file** (AC: #1, #2, #4)
  - [ ] Create `tests/bdd/features/escalate_pipeline_run.feature`:
    - Scenario: Unknown layout triggers escalation
    - Scenario: QA exhaustion triggers escalation
    - Scenario: Operator notified via Telegram
  - [ ] Step definitions with faked ports

- [ ] **Task 7: Write unit tests** (AC: #1)
  - [ ] `tests/unit/application/test_escalate_pipeline_run_use_case.py`
  - [ ] Test: escalation emits correct event type and payload
  - [ ] Test: run status updated to PAUSED
  - [ ] Test: SSE broadcast triggered
  - [ ] Test: Telegram notification sent

## Dev Notes

### Escalation State Machine

The escalation is a sub-state within the main pipeline FSM:

```
PROCESSING ──(unknown layout)──→ PAUSED [escalation: layout_unknown]
PROCESSING ──(QA exhausted)───→ PAUSED [escalation: qa_exhausted]
PROCESSING ──(fatal error)────→ PAUSED [escalation: agent_error]
PAUSED ─────(operator resume)──→ PROCESSING (resumes from last good stage)
```

### Multi-Channel Notification

Escalation notifies through all available channels:
1. **MongoDB event** — persistent record for DVR
2. **SSE broadcast** — real-time UI update
3. **Telegram message** — push notification to operator's phone
4. **Dashboard indicator** — persistent UI banner until resolved

### References

- [Source: prd.md#Functional Requirements] — FR4 (pause for human approval)
- [Source: epics.md#Story 6.1] — Escalate to Operator State Transition
- [Source: architecture.md#Communication Patterns] — Escalation: screenshot + A/B/C options
- [Source: CLAUDE.md#Recovery chain] — retry → fork → fresh → escalate
