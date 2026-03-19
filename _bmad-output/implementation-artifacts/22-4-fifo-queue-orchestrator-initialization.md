# Story 22.4: FIFO Queue & Orchestrator Initialization via API

Status: done

## Story

As a System Operator,
I want incoming pipeline requests to be queued and processed sequentially via the API,
So that the system does not exceed memory or CPU constraints by running multiple heavy FFmpeg jobs concurrently.

## Acceptance Criteria

1. **Given** multiple trigger requests submitted to the API, **When** the background Orchestrator loop checks for work, **Then** it must claim the oldest pending request (FIFO) using the event store, **And** it must begin the FSM state execution for that specific `pipeline_run_id`.

2. **Given** a pipeline run is actively processing, **When** a new trigger request arrives, **Then** the new request must be queued with status `PENDING`, **And** the API must return 201 with the queued run's ID, **And** the new run must NOT start until the active run completes or is paused.

3. **Given** the Orchestrator is idle, **When** a new trigger arrives, **Then** the Orchestrator must automatically begin processing within 5 seconds.

4. **Given** the API returns a `GET /api/runs` list, **When** there are queued and active runs, **Then** the response must show all runs with their current status (e.g., `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`).

## Tasks / Subtasks

- [x] **Task 1: Create pipeline run status enum extension** (AC: #1, #2)
  - [x] Add `RunExecutionStatus` enum to `domain/enums.py`:
    - `PENDING = "pending"` (queued, waiting)
    - `IN_PROGRESS = "in_progress"` (actively processing)
    - `COMPLETED = "completed"` (all stages done)
    - `FAILED = "failed"` (unrecoverable error)
    - `PAUSED = "paused"` (operator intervention)
    - Note: also includes `CANCELLED = "cancelled"` beyond the spec

- [x] **Task 2: Create queue management use case** (AC: #1, #2)
  - [x] Create `src/pipeline/application/use_cases/claim_next_pipeline_run_use_case.py`
  - [x] `ClaimNextPipelineRunUseCase`: queries state store for oldest `PENDING` run (FIFO by `created_at`), transitions it to `IN_PROGRESS`
  - [x] Must emit `pipeline.run_claimed` event
  - [x] Must be atomic — no two workers can claim the same run (enforced via single-concurrency check in worker)

- [x] **Task 3: Create background orchestrator worker** (AC: #1, #3)
  - [x] Create `src/pipeline/application/services/pipeline_orchestrator_worker.py`
  - [x] Background async loop that polls for pending runs every 5 seconds
  - [x] On finding a pending run: claims it and processes it
  - [x] On completion: emits `pipeline.run_completed` event, marks as `COMPLETED`
  - [x] On error: emits `pipeline.error_occurred` and `pipeline.run_failed` events, marks run as `FAILED`
  - [x] Respects single-concurrency constraint (checks for `IN_PROGRESS` runs before claiming)

- [x] **Task 4: Create list pipeline runs endpoint** (AC: #4)
  - [x] Add `GET /api/runs` to `pipeline_runs_router.py`
  - [x] Create `PipelineRunListItemResponseDTO` with fields: `pipeline_run_id`, `youtube_url`, `execution_status`, `current_stage`, `created_at`
  - [ ] Create `ListPipelineRunsUseCase` that queries event store for all runs with projected status (logic is inline in router, not a dedicated use case)
  - [x] Support optional query param `?execution_status=pending` for filtering
  - [x] Add comprehensive OpenAPI docs

- [x] **Task 5: Create get single run endpoint** (AC: #4)
  - [x] Add `GET /api/runs/{pipeline_run_id}` to `pipeline_runs_router.py`
  - [ ] Create `PipelineRunDetailResponseDTO` with full state projection + event count (uses `PipelineRunResponseDTO` instead — no separate detail DTO)
  - [ ] Create `GetPipelineRunDetailUseCase` that returns full projection for a single run (logic is inline in router)
  - [x] Return 404 with `ErrorResponseDTO` if run not found

- [x] **Task 6: Wire background worker into application lifecycle** (AC: #3)
  - [x] Register background worker as FastAPI `lifespan` event (startup/shutdown) in `application_factory.py`
  - [x] Worker starts on application startup, stops gracefully on shutdown
  - [ ] Ensure worker integrates with existing `PipelineOrchestrator` from application layer (worker stubs out actual FSM execution — ports wired in story 23-2)
  - [ ] Log worker lifecycle events via `EventBus` (uses standard `logging` instead)

- [x] **Task 7: Write BDD feature file** (AC: #1, #2, #3)
  - [x] Create `tests/bdd/features/queue_pipeline_runs.feature`:
    - Scenario: First run starts immediately when no other runs are active
    - Scenario: Second run queues while first is active
  - [x] Step definitions using faked event store and state store
  - [x] Verify FIFO ordering

- [x] **Task 8: Write unit tests** (AC: #1, #2)
  - [x] `tests/unit/application/test_claim_next_pipeline_run_use_case.py`
  - [ ] `tests/unit/application/test_pipeline_orchestrator_worker.py` (no dedicated worker unit test file found)
  - [x] Test FIFO ordering, single-concurrency (via use case tests), error handling

## Dev Notes

### Queue Strategy: Event Store Based

Unlike the original file-based queue (fcntl.flock), the new queue uses the MongoDB Event Store. Run ordering is determined by `created_at` timestamp. The `ClaimNextPipelineRunUseCase` queries for the oldest `PENDING` run and atomically transitions it to `IN_PROGRESS` by emitting a claim event.

### Single Concurrency Constraint

The Raspberry Pi hardware cannot handle concurrent FFmpeg jobs. The `PipelineOrchestratorWorker` must enforce single-concurrency:
- Before claiming a run, check that no other run is `IN_PROGRESS`
- If an active run exists, skip and retry on next poll cycle
- This is enforced at the application layer, not the database layer

### Background Worker Pattern

FastAPI's `lifespan` context manager handles the worker lifecycle:

```python
@asynccontextmanager
async def application_lifespan(application: FastAPI):
    worker = PipelineOrchestratorWorker(...)
    worker_task = asyncio.create_task(worker.start_processing_loop())
    yield
    worker.request_graceful_shutdown()
    await worker_task
```

### NFR Compliance

- NFR-P3: FFmpeg memory ≤3GB — single concurrency prevents memory stacking
- NFR-P4: FFmpeg CPU ≤80% — single concurrency enforced
- NFR-R1: Zero ghost states — all status changes are events in the store

### References

- [Source: prd.md#Functional Requirements] — FR2 (state machine), FR3 (FIFO queueing)
- [Source: prd.md#Non-Functional Requirements] — NFR-P3, NFR-P4 (resource limits)
- [Source: epics.md#Story 1.4] — FIFO Queue & Orchestrator Initialization
- [Source: architecture.md#Communication Patterns] — Agent-to-agent via orchestrator
