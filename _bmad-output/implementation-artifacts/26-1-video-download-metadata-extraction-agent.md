# Story 26.1: Video Download & Metadata Extraction Agent

Status: ready-for-dev

## Story

As a System Operator,
I want the pipeline to download the target YouTube video and extract its metadata,
So that subsequent stages have the raw media and context needed to process the Reel.

## Acceptance Criteria

1. **Given** a valid `RunStateProjection` in the download stage, **When** the corresponding Application Use Case is executed, **Then** `yt-dlp` must be invoked to download the video/audio, **And** the generated assets must be stored via `FileStoragePort`, **And** a `stage_completed` event with asset metadata must be persisted.

2. **Given** a YouTube URL with available subtitles, **When** the download stage runs, **Then** subtitles/transcripts must also be downloaded and stored.

3. **Given** the existing `YtDlpDownloader` adapter, **When** integrating into the new architecture, **Then** it must be wrapped to emit events via `PipelineEventEmitterService` at each step (download started, video downloaded, subtitles downloaded, metadata extracted).

4. **Given** the download fails (network error, unavailable video), **When** the error occurs, **Then** an `error_occurred` event must be emitted, **And** the run must transition to `FAILED` or enter recovery.

## Tasks / Subtasks

- [ ] **Task 1: Create download video use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/download_video_use_case.py`
  - [ ] `DownloadVideoUseCase` with injected: `VideoDownloadPort`, `FileStoragePort`, `PipelineEventEmitterService`
  - [ ] Steps:
    1. Emit `stage_entered` event
    2. Download video via `VideoDownloadPort`
    3. Save video to `FileStoragePort`
    4. Download subtitles (if available)
    5. Extract metadata
    6. Emit `stage_completed` with artifact paths and metadata
  - [ ] Return Result monad

- [ ] **Task 2: Wrap existing YtDlpDownloader for event emission** (AC: #3)
  - [ ] Existing adapter at `infrastructure/adapters/ytdlp_adapter.py` stays as-is
  - [ ] Create wrapper or update use case to emit events at each step
  - [ ] No changes to the adapter itself — just the use case orchestration adds events

- [ ] **Task 3: Create download output DTO** (AC: #1)
  - [ ] Create `presentation/dtos/download_output_dto.py`:
    - `video_file_path: str`
    - `audio_file_path: str | None`
    - `subtitle_file_path: str | None`
    - `video_metadata: VideoMetadataDTO` (title, duration, channel, url)
  - [ ] Create mapper: `DownloadOutputDTO` → domain event payload

- [ ] **Task 4: Create MCP tool for agent-driven download** (AC: #1)
  - [ ] If the download stage is agent-driven: create `trigger_video_download` MCP tool
  - [ ] If orchestrator-driven: the use case is called directly by the orchestrator
  - [ ] Document which approach is used based on existing pipeline behavior

- [ ] **Task 5: Write BDD feature file** (AC: #1, #2, #4)
  - [ ] Create `tests/bdd/features/download_video.feature`:
    - Scenario: Successfully download video and subtitles
    - Scenario: Download video without subtitles available
    - Scenario: Download fails with network error
  - [ ] Step definitions with faked ports

- [ ] **Task 6: Write unit tests** (AC: #1, #4)
  - [ ] `tests/unit/application/test_download_video_use_case.py`
  - [ ] Test: successful download → events emitted → artifacts saved
  - [ ] Test: download failure → error event emitted
  - [ ] Test: subtitles unavailable → proceeds without error

## Dev Notes

### Migration Strategy

The existing pipeline has a working download mechanism via `YtDlpDownloader` adapter and the Research agent. The refactor preserves this adapter but wraps its usage in the new event-driven use case pattern. Key changes:
- **Before**: Orchestrator calls adapter directly, writes state to filesystem
- **After**: Use case calls adapter, saves via `FileStoragePort`, emits events to MongoDB

### Binary Asset Strategy

Downloaded videos are binary assets → saved to filesystem via `FileStoragePort`. Only the path is recorded in the MongoDB event:

```python
payload_data = {
    "video_file_path": "runs/run-abc/source-video.mp4",
    "subtitle_file_path": "runs/run-abc/subtitles.vtt",
    "duration_seconds": 3600,
    "title": "Podcast Episode 42",
}
```

### References

- [Source: prd.md#Core Processing] — FR16 (download video, audio, metadata)
- [Source: epics.md#Story 5.1] — Video Download & Metadata Extraction Agent
- [Source: architecture.md#Port Boundaries] — VideoDownloadPort → YtDlpDownloader
