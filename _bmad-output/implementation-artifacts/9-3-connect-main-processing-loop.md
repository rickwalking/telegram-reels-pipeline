# Story 9.3: Connect Main Processing Loop to PipelineRunner

Status: ready-for-dev

## Story

As a developer,
I want main.py's processing loop to call PipelineRunner.run() for each queue item,
So that URLs sent via Telegram are actually processed through the full pipeline.

## Acceptance Criteria

1. **Given** a queue item is claimed in main.py's while loop,
   **When** a workspace is created,
   **Then** `pipeline_runner.run(item, workspace)` is called,
   **And** the queue item is marked completed only after the pipeline finishes.

2. **Given** PipelineRunner.run() raises an exception,
   **When** the error is caught,
   **Then** the queue item is moved to a failed state (not completed),
   **And** the user is notified via Telegram with an error summary,
   **And** the error is logged with full traceback.

3. **Given** a pipeline run pauses for escalation (unknown layout, QA exhaustion),
   **When** PipelineRunner returns a state with `escalation_state != NONE`,
   **Then** the queue item remains in processing (not completed),
   **And** a subsequent poll can detect and resume it.

4. **Given** the pipeline is running,
   **When** I inspect the main.py processing loop,
   **Then** there is no stub comment ("Pipeline execution would happen here"),
   **And** actual pipeline execution replaces the stub.

## Tasks / Subtasks

- [ ] Task 1: Replace main.py stub with PipelineRunner call (AC: #1, #4)
  - [ ] Remove the stub comment block at lines 55-58
  - [ ] Add `state = await orchestrator.pipeline_runner.run(item, workspace)`
  - [ ] Guard: only call if `orchestrator.pipeline_runner is not None`
  - [ ] If pipeline_runner is None, log warning and skip

- [ ] Task 2: Add QueueConsumer.fail() method (AC: #2)
  - [ ] QueueConsumer currently only has `complete(processing_path)` — NO fail() method exists
  - [ ] Add `fail(processing_path: Path) -> Path` that moves item to a new `failed/` directory
  - [ ] Add `self._failed = base_dir / "failed"` in `__init__`
  - [ ] Update `ensure_dirs()` to also create `failed/`
  - [ ] Add tests for fail() method

- [ ] Task 3: Add error handling around pipeline execution (AC: #2)
  - [ ] Wrap `pipeline_runner.run()` in try/except
  - [ ] On `PipelineError`: log, notify user via Telegram, call `queue_consumer.fail(processing_path)`
  - [ ] On unexpected `Exception`: log with traceback, notify user, call `queue_consumer.fail(processing_path)`
  - [ ] Always use exception chaining: `raise X from Y`

- [ ] Task 4: Handle escalation pauses (AC: #3)
  - [ ] Check returned `RunState.escalation_state`
  - [ ] If `escalation_state != EscalationState.NONE`: do NOT call `queue_consumer.complete()`
  - [ ] Leave item in `processing/` — subsequent polls can detect it
  - [ ] Log the escalation state and paused run_id
  - [ ] Note: user notification is handled by PipelineRunner event bus, not main.py

- [ ] Task 5: Test and validate (AC: #1-#4)
  - [ ] Add test: QueueConsumer.fail() moves item to failed/
  - [ ] Add test: pipeline failure calls fail(), not complete()
  - [ ] Add test: escalation leaves item in processing/
  - [ ] Run full test suite and linters

## Dev Notes

### Current main.py Stub (lines 55-58)

```python
async with orchestrator.workspace_manager.managed_workspace() as workspace:
    logger.info("Workspace created: %s", workspace)
    # Pipeline execution would happen here
    # For now, just log the URL
```

Replace with actual PipelineRunner execution. Keep the workspace context manager — PipelineRunner.run() receives the workspace path.

### Error Handling Pattern

```python
try:
    state = await orchestrator.pipeline_runner.run(item, workspace)
    if state.escalation_state != EscalationState.NONE:
        logger.warning("Run %s paused — escalation: %s", state.run_id, state.escalation_state.value)
        # Don't complete — leave in processing for resume
    else:
        orchestrator.queue_consumer.complete(processing_path)
except PipelineError as exc:
    logger.error("Pipeline failed for %s: %s", item.url, exc)
    # Move to failed, notify user
except Exception as exc:
    logger.exception("Unexpected error processing %s", item.url)
    # Move to failed, notify user
```

### Queue Consumer Methods (verified from source)

`QueueConsumer` currently has:
- `enqueue(item)` — adds to inbox/
- `claim_next()` — moves from inbox/ to processing/
- `complete(processing_path)` — moves from processing/ to completed/

Missing (must be added in this story):
- `fail(processing_path)` — moves from processing/ to failed/
- `failed/` directory does not exist yet — must be added to `ensure_dirs()`

### Existing File Locations

```
src/pipeline/app/main.py                        # Entry point with stub
src/pipeline/application/queue_consumer.py       # QueueConsumer
src/pipeline/domain/enums.py                     # EscalationState
src/pipeline/domain/errors.py                    # PipelineError
```

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 4] — Pipeline never executes
- [Source: main.py:55-58] — Stub comment block

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
