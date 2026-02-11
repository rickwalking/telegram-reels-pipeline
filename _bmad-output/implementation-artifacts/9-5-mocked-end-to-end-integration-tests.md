# Story 9.5: Mocked End-to-End Integration Tests

Status: ready-for-dev

## Story

As a developer,
I want integration tests that exercise the full pipeline with fake adapters,
So that I can verify all stages, QA gates, recovery, and delivery work together without external services.

## Acceptance Criteria

1. **Given** a fake adapter implementation for each port,
   **When** PipelineRunner.run() executes with a test QueueItem,
   **Then** all 8 stages execute in sequence (ROUTER through DELIVERY),
   **And** the final RunState has `current_stage == COMPLETED`.

2. **Given** a fake agent that returns REWORK on first QA attempt,
   **When** the ReflectionLoop processes the stage,
   **Then** the agent is re-invoked with prescriptive feedback,
   **And** the second attempt passes QA,
   **And** the pipeline continues to the next stage.

3. **Given** a fake agent that fails all 3 QA attempts,
   **When** best-of-three selection activates,
   **Then** the highest-scoring attempt is selected,
   **And** the pipeline continues (or escalates if score < threshold).

4. **Given** a pipeline run that crashes mid-execution,
   **When** CrashRecoveryHandler scans on restart,
   **Then** the interrupted run is detected,
   **And** PipelineRunner.resume() starts from the correct stage.

5. **Given** the DELIVERY stage completes,
   **When** DeliveryHandler is invoked,
   **Then** it calls MessagingPort.send_file() with the video path,
   **And** it sends content metadata (descriptions, hashtags) via MessagingPort.notify_user().

6. **Given** all integration tests pass,
   **When** I check coverage,
   **Then** integration tests cover the happy path, QA rework, recovery, and delivery flows.

## Tasks / Subtasks

- [ ] Task 1: Create fake adapter implementations (AC: #1)
  - [ ] `FakeAgentBackend(AgentExecutionPort)` — returns canned AgentResult
  - [ ] `FakeModelDispatch(ModelDispatchPort)` — returns canned QA JSON
  - [ ] `FakeMessaging(MessagingPort)` — records sent messages
  - [ ] `FakeVideoProcessor(VideoProcessingPort)` — creates empty output files
  - [ ] `FakeVideoDownloader(VideoDownloadPort)` — creates dummy metadata/subtitles
  - [ ] `FakeStateStore(StateStorePort)` — in-memory dict
  - [ ] `FakeFileDelivery(FileDeliveryPort)` — returns fake URL
  - [ ] Place in `tests/integration/fakes.py`

- [ ] Task 2: Happy path integration test (AC: #1, #5)
  - [ ] Create test `test_full_pipeline_happy_path`
  - [ ] Wire PipelineRunner with all fakes
  - [ ] Create dummy workflow files (stage-XX.md, agent.md, gate criteria) in tmp dir
  - [ ] Submit a QueueItem with a test URL
  - [ ] Assert: RunState.current_stage == COMPLETED
  - [ ] Assert: FakeMessaging received delivery messages

- [ ] Task 3: QA rework integration test (AC: #2)
  - [ ] Configure FakeModelDispatch to return REWORK on attempt 1, PASS on attempt 2
  - [ ] Run pipeline
  - [ ] Assert: agent was called twice for the rework stage
  - [ ] Assert: pipeline completed successfully

- [ ] Task 4: QA exhaustion / best-of-three test (AC: #3)
  - [ ] Configure FakeModelDispatch to return REWORK 3 times with varying scores
  - [ ] Run pipeline
  - [ ] Assert: best attempt selected (highest score)
  - [ ] Assert: pipeline continues if score >= threshold, escalates if below

- [ ] Task 5: Crash recovery integration test (AC: #4)
  - [ ] Use FakeStateStore pre-loaded with an interrupted RunState
  - [ ] Call CrashRecoveryHandler.scan_and_recover()
  - [ ] Feed recovery plan into PipelineRunner.resume()
  - [ ] Assert: pipeline resumes from correct stage, not from beginning

- [ ] Task 6: Run and validate (AC: #6)
  - [ ] `poetry run pytest tests/integration/ -x -q`
  - [ ] Verify all integration tests pass
  - [ ] Run linters

## Dev Notes

### Fake Adapter Strategy

Use in-memory fakes (not mocks) per project convention. Each fake should:
- Implement the corresponding Port Protocol
- Record calls for assertion (e.g., `FakeMessaging.sent_messages: list[str]`)
- Return predictable, configurable responses
- Be reusable across multiple tests

### Dummy Workflow Files

Integration tests need stage files, agent definitions, and gate criteria to exist on disk (PipelineRunner reads them). Create minimal dummy files in `tmp_path` fixture:
```
{tmp_path}/workflows/stages/stage-01-router.md  → "# Router Stage\nProcess the URL."
{tmp_path}/agents/router/agent.md               → "# Router Agent\nYou are the router."
{tmp_path}/workflows/qa/gate-criteria/router-criteria.md → "- URL is valid"
```

### Test File Location

```
tests/integration/fakes.py              # Shared fake implementations
tests/integration/test_pipeline_e2e.py  # End-to-end pipeline tests
tests/integration/test_recovery.py      # Crash recovery tests
```

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 7] — No integration tests
- [Source: pipeline_runner.py] — PipelineRunner.run() method
- [Source: reflection_loop.py] — ReflectionLoop QA cycle
- [Source: crash_recovery.py] — CrashRecoveryHandler

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
