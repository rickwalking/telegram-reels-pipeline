# Story 1.6: Queue Management & Workspace Isolation

Status: done

## Story

As a developer,
I want a FIFO queue for pipeline requests and isolated per-run workspaces,
so that concurrent requests are queued safely and each run's artifacts are contained. (FR38, FR39)

## Acceptance Criteria

1. Given a new pipeline request arrives, when the queue_consumer checks for work, then the oldest item in queue/inbox/ is claimed by moving to queue/processing/ and file locking (flock) prevents duplicate claims
2. Given a run is already in progress and a new URL is submitted, when the queue receives the request, then it is queued in inbox/ with a timestamp-prefixed JSON file
3. Given a run is claimed, when the workspace_manager creates a workspace, then a new directory is created under workspace/runs/<timestamp>-<short_id>/ and all stage outputs are scoped to this workspace
4. Given a run completes, when the workspace context manager exits, then the queue item moves from processing/ to completed/

## Tasks / Subtasks

- [x] Task 1: Implement QueueConsumer in application layer (AC: 1, 2)
- [x] Task 2: Implement WorkspaceManager in application layer (AC: 3, 4)
- [x] Task 3: Write comprehensive tests

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 247 tests passing, 96.99% coverage, all linters clean
- QueueConsumer: FIFO with fcntl.flock, inbox→processing→completed lifecycle
- WorkspaceManager: per-run dirs with UUID, async context manager, list_workspaces
- 25 new tests across 2 test files
- Review fix: queue filenames now include UUID suffix to prevent timestamp collision
- Review fix: lock cleanup moved to finally block to prevent stranded lock files

### File List

- src/pipeline/application/queue_consumer.py (NEW)
- src/pipeline/application/workspace_manager.py (NEW)
- tests/unit/application/test_queue_consumer.py (NEW)
- tests/unit/application/test_workspace_manager.py (NEW)

