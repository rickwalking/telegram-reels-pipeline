# Story 23.4: Local File System Adapter for Binary Media

Status: ready-for-dev

## Story

As a Developer,
I want to create a `FileStorageAdapter` for saving heavy binary assets (videos, images),
So that the MongoDB instance is kept lightweight and only handles JSON event data.

## Acceptance Criteria

1. **Given** the pipeline needs to save a downloaded video or generated thumbnail, **When** the save command is issued via the `FileStoragePort`, **Then** the media must be written to a local `workspace/runs/{pipeline_run_id}/` directory using atomic write (temp + rename).

2. **Given** a binary asset is saved, **When** the event is recorded in MongoDB, **Then** only the file path (not the binary data) must be stored in the event payload.

3. **Given** multiple pipeline runs, **When** assets are saved, **Then** each run's files must be in isolated directories, **And** no cross-run file path contamination is possible.

4. **Given** the `FileStoragePort` protocol, **When** the adapter is tested, **Then** it must conform to the protocol contract, **And** integration tests must verify real filesystem operations.

## Tasks / Subtasks

- [ ] **Task 1: Define FileStoragePort protocol** (AC: #1, #2)
  - [ ] Ensure `domain/ports/file_storage_port.py` defines:
    - `async save_binary_asset(pipeline_run_id: str, asset_name: str, binary_content: bytes) -> str` (returns relative path)
    - `async save_binary_asset_from_path(pipeline_run_id: str, asset_name: str, source_path: str) -> str` (move/copy file)
    - `async get_asset_absolute_path(pipeline_run_id: str, asset_name: str) -> str`
    - `async list_run_assets(pipeline_run_id: str) -> tuple[str, ...]`
    - `async delete_run_assets(pipeline_run_id: str) -> None`

- [ ] **Task 2: Implement LocalFileStorageAdapter** (AC: #1, #2, #3)
  - [ ] Create `src/pipeline/infrastructure/adapters/local_file_storage_adapter.py`
  - [ ] Constructor accepts `workspace_base_directory: str`
  - [ ] `save_binary_asset()`:
    - Create run directory if not exists: `{workspace_base_directory}/runs/{pipeline_run_id}/`
    - Atomic write: write to `.tmp` file, then `os.rename()` to final path
    - Return relative path: `runs/{pipeline_run_id}/{asset_name}`
  - [ ] `save_binary_asset_from_path()`:
    - Move or copy source file to run directory atomically
  - [ ] `get_asset_absolute_path()`:
    - Resolve and validate path (prevent directory traversal)
    - Return absolute path
  - [ ] `list_run_assets()`:
    - List files in run directory
  - [ ] `delete_run_assets()`:
    - Remove entire run directory (for cleanup)

- [ ] **Task 3: Add path validation and security** (AC: #3)
  - [ ] Validate `asset_name` does not contain `..` or absolute paths
  - [ ] Validate `pipeline_run_id` matches expected format (prevent injection)
  - [ ] All paths resolved via `pathlib.Path.resolve()` and checked against workspace root
  - [ ] Raise `DomainValidationError` on path traversal attempts

- [ ] **Task 4: Integrate with event payload pattern** (AC: #2)
  - [ ] Document the convention: when saving binary assets, include only the **relative path** in event payloads
  - [ ] Example event payload: `{"artifact_paths": ("runs/run-abc/final-reel.mp4",)}`
  - [ ] The Presentation layer can later resolve relative paths to serve files via HTTP

- [ ] **Task 5: Create workspace cleanup service** (AC: #3)
  - [ ] Create `src/pipeline/application/services/workspace_cleanup_service.py`
  - [ ] `WorkspaceCleanupService` with configurable retention period (default: 30 days)
  - [ ] `async cleanup_expired_workspaces() -> int` (returns count deleted)
  - [ ] Only deletes runs that are `COMPLETED` or `FAILED` and older than retention period
  - [ ] Emits `workspace.cleaned` event for audit trail

- [ ] **Task 6: Write integration tests** (AC: #1, #3, #4)
  - [ ] `tests/integration/test_local_file_storage_adapter.py`
  - [ ] Test: save binary → file exists on disk
  - [ ] Test: save from path → file moved atomically
  - [ ] Test: isolated directories per run
  - [ ] Test: path traversal rejection
  - [ ] Test: list assets, delete assets
  - [ ] Use `tmp_path` pytest fixture for test isolation

- [ ] **Task 7: Write unit tests** (AC: #1)
  - [ ] `tests/unit/application/test_workspace_cleanup_service.py`
  - [ ] Test: expired runs cleaned up
  - [ ] Test: active runs preserved
  - [ ] Test: retention period respected

## Dev Notes

### Separation of Concerns: MongoDB vs Filesystem

| Data Type | Storage | Reason |
|-----------|---------|--------|
| Pipeline events (JSON) | MongoDB | Queryable, event sourcing, time-travel |
| State projections (JSON) | MongoDB | Fast reads for API/SSE |
| Videos (.mp4) | Local filesystem | Too large for DB, FFmpeg needs file paths |
| Images (.png, .jpg) | Local filesystem | Frame extraction output, thumbnails |
| Transcripts (.txt, .vtt) | MongoDB event payload | Small enough to inline, needed for time-travel |

### Atomic Write Pattern

Per CLAUDE.md, all state file mutations use write-to-temp + rename:

```python
temporary_file_path = final_path.with_suffix(".tmp")
temporary_file_path.write_bytes(binary_content)
temporary_file_path.rename(final_path)  # atomic on same filesystem
```

### Workspace Directory Structure

```
workspace/
└── runs/
    ├── run-abc123/
    │   ├── source-video.mp4
    │   ├── transcript_clean.txt
    │   ├── frames/
    │   │   ├── frame-001.png
    │   │   └── frame-002.png
    │   ├── segment-001.mp4
    │   └── final-reel.mp4
    └── run-def456/
        └── ...
```

### References

- [Source: prd.md#Functional Requirements] — FR8 (binary media persistence)
- [Source: prd.md#Risk Mitigation] — Raspberry Pi memory limits, binary on filesystem
- [Source: epics.md#Story 2.4] — Local File System Adapter for Binary Media
- [Source: architecture.md#Data Architecture] — Artifacts in per-run `assets/` directory
- [Source: CLAUDE.md#Process Patterns] — Atomic state writes
