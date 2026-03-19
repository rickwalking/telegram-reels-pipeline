# Story 27.3: Resume Pipeline API Endpoint

Status: ready-for-dev

## Story

As a System Operator,
I want to resume a paused pipeline run via the REST API,
So that after I have corrected an error or approved a step, the agents can continue.

## Acceptance Criteria

1. **Given** a pipeline run in `PAUSED` or `ESCALATED` state, **When** a `POST /api/runs/{pipeline_run_id}/resume` request is made, **Then** the Orchestrator must reload the run state from MongoDB, **And** identify the next stage based on the event stream, **And** resume FSM execution, **And** emit a `pipeline.resumed` event.

2. **Given** the optional `resume_from_stage` parameter, **When** provided, **Then** the pipeline must restart from that specific stage (overriding automatic detection), **And** a `pipeline.stage_override` event must be emitted.

3. **Given** a running pipeline, **When** a resume request is made, **Then** the API must return 409 Conflict.

4. **Given** the UI, **When** the pipeline resumes, **Then** the SSE stream must immediately reflect the `IN_PROGRESS` state and begin streaming new events.

## Tasks / Subtasks

- [ ] **Task 1: Create resume API endpoint** (AC: #1, #2, #3)
  - [ ] Add `POST /api/runs/{pipeline_run_id}/resume` to `pipeline_runs_router.py`
  - [ ] Request body: optional `resume_from_stage: str | None`, optional `operator_notes: str | None`
  - [ ] Validate run is in a resumable state (PAUSED)
  - [ ] Return 200 on success with updated run state, 409 if already running, 400 if not resumable

- [ ] **Task 2: Create resume use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/resume_pipeline_run_use_case.py`
  - [ ] `ResumePipelineRunUseCase` with injected: `EventStorePort`, `StateStorePort`, `SseBroadcastPort`
  - [ ] Steps:
    1. Load run state from projection
    2. Validate it's resumable (PAUSED or has escalation)
    3. Determine resume point:
       - If `resume_from_stage` provided: use that stage
       - Otherwise: replay events to find next incomplete stage
    4. Emit `pipeline.resumed` event (include operator notes if any)
    5. Update projection: `execution_status = IN_PROGRESS`, `escalation_status = NONE`
    6. Signal orchestrator worker to pick up this run
    7. Broadcast resume event via SSE

- [ ] **Task 3: Create resume point detection** (AC: #1)
  - [ ] Create `src/pipeline/application/services/resume_point_detector_service.py`
  - [ ] `detect_resume_point(events: tuple[PipelineStateEvent, ...]) -> str`
  - [ ] Logic:
    - Find the last `stage_completed` event → next stage is the resume point
    - If last event is `stage_entered` without completion → resume from that stage
    - If last event is `qa.gate_rework` → resume from rework of that stage
  - [ ] Pure function operating on event data

- [ ] **Task 4: Implement stage override mechanism** (AC: #2)
  - [ ] When `resume_from_stage` is provided:
    - Validate the stage name is valid
    - Emit `pipeline.stage_override` event with the override stage
    - Orchestrator starts from the specified stage, replaying necessary context
  - [ ] This enables "go back and redo" scenarios

- [ ] **Task 5: Add resume button to React UI** (AC: #4)
  - [ ] Add "Resume Pipeline" button to `RunDetailPage.tsx` (visible when PAUSED)
  - [ ] Optional: dropdown to select resume-from-stage
  - [ ] Optional: text input for operator notes
  - [ ] After resume: button returns to "Pause Pipeline"
  - [ ] SSE stream resumes delivering events

- [ ] **Task 6: Wire resume signal to orchestrator worker** (AC: #1)
  - [ ] When resume use case completes:
    - Signal `PipelineOrchestratorWorker` to check for resumable runs
    - Worker picks up the run and resumes processing
  - [ ] Use async event or queue to deliver the signal

- [ ] **Task 7: Write BDD feature file** (AC: #1, #2, #3)
  - [ ] Create `tests/bdd/features/resume_pipeline_run.feature`:
    - Scenario: Resume paused run from last completed stage
    - Scenario: Resume with stage override
    - Scenario: Attempt to resume already-running run
  - [ ] Step definitions with faked stores

- [ ] **Task 8: Write unit tests** (AC: #1, #2)
  - [ ] `tests/unit/application/test_resume_pipeline_run_use_case.py`
  - [ ] `tests/unit/application/test_resume_point_detector_service.py`
  - [ ] Test: auto-detect resume point from events
  - [ ] Test: stage override changes resume point
  - [ ] Test: resume emits correct events

## Dev Notes

### Resume Point Detection Algorithm

```python
def detect_resume_point(
    pipeline_events: tuple[PipelineStateEvent, ...],
) -> str:
    """Analyze event stream to determine where to resume."""
    last_completed_stage = None
    for event in reversed(pipeline_events):
        if event.event_type == "pipeline.stage_completed":
            last_completed_stage = event.stage_name
            break

    if last_completed_stage is None:
        return "router"  # Start from beginning

    return get_next_stage_after(last_completed_stage)
```

### Operator Notes Pattern

When an operator resumes after an escalation, they may want to leave notes explaining what they changed. These notes are stored in the `pipeline.resumed` event payload:

```python
payload_data = {
    "resume_from_stage": "layout_detective",
    "operator_notes": "Updated crop strategy for new dual-camera layout",
    "escalation_resolved": "layout_unknown",
}
```

These notes appear in the DVR timeline, providing context for future debugging.

### Full Pause/Resume Lifecycle

```
IN_PROGRESS ──(POST /pause)──→ PAUSED ──(POST /resume)──→ IN_PROGRESS
                                  │
                          [Operator inspects DVR]
                          [Operator fixes config]
                          [Operator adds notes]
                                  │
                          (POST /resume with stage override)
                                  ↓
                            IN_PROGRESS (from specified stage)
```

### References

- [Source: prd.md#Functional Requirements] — FR5 (resume from checkpoint)
- [Source: prd.md#User Journeys] — Journey 2: resume from checkpoint in UI
- [Source: epics.md#Story 6.3] — Resume Pipeline API Endpoint
- [Source: CLAUDE.md#Running the Pipeline] — `--resume` flag with `--start-stage`
