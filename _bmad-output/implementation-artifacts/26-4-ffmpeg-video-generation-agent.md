# Story 26.4: FFmpeg Video Generation Agent

Status: ready-for-dev

## Story

As a System Operator,
I want the pipeline to execute FFmpeg commands based on the layout decision,
So that the final 1080x1920 Reel is rendered correctly with proper cropping and encoding.

## Acceptance Criteria

1. **Given** a completed layout decision and source video, **When** the FFmpeg Engineer agent executes, **Then** it must generate cropped and encoded video segments respecting memory (≤3GB) and CPU (≤80%) limits, **And** emit a `stage_completed` event with segment metadata.

2. **Given** the encoding plan, **When** segments are produced, **Then** each segment must be saved via `FileStoragePort`, **And** only the file paths must be recorded in the event payload.

3. **Given** the framing style FSM, **When** style transitions occur between segments, **Then** the encoding plan must include transition metadata (fade durations, style change points).

4. **Given** the quality check script, **When** a segment is produced, **Then** upscale quality and sharpness must be validated, **And** quality results must be included in the event payload.

## Tasks / Subtasks

- [ ] **Task 1: Create FFmpeg encoding use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/generate_video_segments_use_case.py`
  - [ ] `GenerateVideoSegmentsUseCase` with injected: `VideoProcessingPort`, `FileStoragePort`, `AgentExecutionPort`, `PipelineEventEmitterService`
  - [ ] Steps:
    1. Load layout decision from prior stage event
    2. Agent generates encoding plan (crop regions, styles, transitions)
    3. Validate plan via `FfmpegEncodingPlanDTO`
    4. Execute FFmpeg via `VideoProcessingPort` for each segment
    5. Save segments via `FileStoragePort`
    6. Run quality checks
    7. Emit `stage_completed` with segment paths and quality data

- [ ] **Task 2: Create FfmpegEncodingPlanDTO** (AC: #1, #3)
  - [ ] `presentation/dtos/ffmpeg_encoding_plan_dto.py`:
    - `segments: list[VideoSegmentDTO]` with: `start_seconds`, `end_seconds`, `crop_region`, `framing_style`
    - `style_transitions: list[StyleTransitionDTO]` with: `timestamp`, `from_style`, `to_style`, `transition_type`
    - `encoding_parameters: EncodingParametersDTO` with: `codec`, `bitrate`, `thread_count`, `resolution`
  - [ ] Validators: segment ranges non-overlapping, crop within source dimensions

- [ ] **Task 3: Wrap existing FFmpeg adapter for event emission** (AC: #1, #2)
  - [ ] Existing `FFmpegProcessor` adapter handles actual FFmpeg execution
  - [ ] Use case handles event emission and file storage
  - [ ] Ensure adapter respects resource limits (thread count, memory)

- [ ] **Task 4: Integrate quality validation** (AC: #4)
  - [ ] Create quality check step in use case:
    - Run `check_upscale_quality` logic via port
    - Include quality results (sharpness score, upscale factor) in event payload
  - [ ] If quality fails threshold: enter QA rework cycle

- [ ] **Task 5: Write BDD feature file** (AC: #1, #2, #4)
  - [ ] Create `tests/bdd/features/generate_video_segments.feature`:
    - Scenario: Generate segments for solo layout
    - Scenario: Generate segments with style transitions
    - Scenario: Quality check fails → rework
  - [ ] Step definitions with faked ports

- [ ] **Task 6: Write unit tests** (AC: #1, #2, #3, #4)
  - [ ] `tests/unit/application/test_generate_video_segments_use_case.py`
  - [ ] `tests/unit/presentation/test_ffmpeg_encoding_plan_dto.py`
  - [ ] Test: encoding plan validation (overlapping segments rejected)
  - [ ] Test: segments saved with correct paths
  - [ ] Test: quality check results in event payload

## Dev Notes

### Resource Constraints (Raspberry Pi)

Per NFR-P3 and NFR-P4:
- FFmpeg memory ≤3GB peak → use `-threads 2` and limit concurrent FFmpeg processes
- FFmpeg CPU ≤80% → `CPUQuota=80%` via systemd, `thread_count` in encoding params
- Single concurrency (from Story 22-4) prevents resource stacking

### File Storage for Video Segments

Video segments are large binary files → always saved via `FileStoragePort`. The event payload only contains paths:

```python
payload_data = {
    "segment_paths": ("runs/run-abc/segment-001.mp4", "runs/run-abc/segment-002.mp4"),
    "encoding_plan": {... encoding parameters ...},
    "quality_results": {"sharpness_score": 0.87, "upscale_factor": 1.8},
}
```

### Framing Style FSM Integration

The encoding plan must include framing style information from the domain FSM (`domain/transitions.py`). Style transitions between segments drive the assembly stage's xfade parameters.

### References

- [Source: prd.md#Core Processing] — FR19 (FFmpeg 1080x1920 generation)
- [Source: prd.md#Non-Functional Requirements] — NFR-P3 (memory), NFR-P4 (CPU)
- [Source: epics.md#Story 5.4] — FFmpeg Video Generation Agent
- [Source: CLAUDE.md#Pipeline Stages] — Stage 6: FFmpeg Engineer
- [Source: CLAUDE.md#Framing Style FSM] — 5 states with event-driven transitions
