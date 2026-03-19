# Story 26.3: Camera Layout Detection Agent

Status: ready-for-dev

## Story

As a System Operator,
I want the system to analyze the selected video segment and determine the optimal crop strategy,
So that the final Reel correctly frames the speakers without manual cropping.

## Acceptance Criteria

1. **Given** the selected video timestamps, **When** the Layout Detection agent runs, **Then** it must extract frames, analyze faces, and output a `LayoutAnalysisOutputDTO`, **And** the decision must be committed as a `stage_completed` event.

2. **Given** the face detection results, **When** the layout is classified, **Then** the hybrid face gate must produce per-frame duo scores, EMA scores, shot types, and gate reasons.

3. **Given** an unknown layout, **When** detected, **Then** the agent must emit an `escalation_triggered` event, **And** the pipeline must transition to the escalation state (linking to Epic 27).

4. **Given** the existing face detection and VTT parsing scripts, **When** integrating, **Then** they must be invoked via `VideoProcessingPort` adapter, not called directly by the use case.

## Tasks / Subtasks

- [ ] **Task 1: Create layout detection use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/detect_camera_layout_use_case.py`
  - [ ] `DetectCameraLayoutUseCase` with injected: `VideoProcessingPort`, `AgentExecutionPort`, `PipelineEventEmitterService`
  - [ ] Steps:
    1. Load selected timestamps from prior stage event
    2. Extract frames via `VideoProcessingPort`
    3. Run face detection via `VideoProcessingPort`
    4. Run hybrid face gate analysis
    5. Agent analyzes results and produces layout decision
    6. Validate via `LayoutAnalysisOutputDTO` (Gate 1 + Gate 2)
    7. Emit `stage_completed` event with layout data

- [ ] **Task 2: Create LayoutAnalysisOutputDTO** (AC: #1, #2)
  - [ ] `presentation/dtos/layout_analysis_output_dto.py`:
    - `layout_classification: str` (solo, duo_split, duo_pip, screen_share, cinematic_solo)
    - `face_position_data: list[FacePositionItemDTO]` (per-frame face coordinates)
    - `speaker_timeline_data: list[SpeakerTimelineItemDTO]` (VTT-derived speaker changes)
    - `hybrid_gate_results: list[HybridGateResultDTO]` (duo_score, ema_score, shot_type)
    - `framing_style_recommendation: str`

- [ ] **Task 3: Handle escalation for unknown layouts** (AC: #3)
  - [ ] When layout agent returns `LayoutUnknown` classification:
    - Emit `escalation_triggered` event with screenshot and context
    - Transition run to `PAUSED` with `escalation_status = LAYOUT_UNKNOWN`
    - Notify operator via SSE (if connected) and Telegram
  - [ ] The resume path is handled by Epic 27 stories

- [ ] **Task 4: Wrap existing face detection scripts as VideoProcessingPort methods** (AC: #4)
  - [ ] Ensure `VideoProcessingPort` includes:
    - `extract_analysis_frames(video_path: str, timestamps: tuple[float, ...]) -> tuple[str, ...]`
    - `detect_faces_in_frames(frames_directory: str) -> FaceDetectionResult`
    - `parse_vtt_speaker_timeline(vtt_path: str, start_seconds: float, end_seconds: float) -> SpeakerTimeline`
  - [ ] Existing `detect_faces.py` and `parse_vtt_speakers.py` are invoked by the infrastructure adapter
  - [ ] The application use case only sees the port interface

- [ ] **Task 5: Write BDD feature file** (AC: #1, #3)
  - [ ] Create `tests/bdd/features/detect_camera_layout.feature`:
    - Scenario: Detect solo speaker layout
    - Scenario: Detect duo split-screen layout
    - Scenario: Unknown layout triggers escalation
  - [ ] Step definitions with faked video processing port

- [ ] **Task 6: Write unit tests** (AC: #1, #2, #3)
  - [ ] `tests/unit/application/test_detect_camera_layout_use_case.py`
  - [ ] `tests/unit/presentation/test_layout_analysis_output_dto.py`
  - [ ] Test: known layout → event emitted
  - [ ] Test: unknown layout → escalation event
  - [ ] Test: face gate results validated

## Dev Notes

### Face Detection Pipeline (Existing)

The existing pipeline runs:
1. `parse_vtt_speakers.py` — VTT speaker timeline
2. `detect_faces.py --gate` — face detection with hybrid gate
3. Agent analyzes combined data → layout decision

In the new architecture, these scripts are invoked by `FFmpegProcessor` or a dedicated `FaceDetectionAdapter` implementing `VideoProcessingPort`. The use case orchestrates the sequence.

### Hybrid Face Gate Integration

The hybrid face gate (`domain/face_gate.py`) is a pure domain function. It takes face detection data and produces duo scores. It should remain in the domain layer. The use case calls it directly (domain is importable by application).

### References

- [Source: prd.md#Core Processing] — FR18 (camera layout detection)
- [Source: epics.md#Story 5.3] — Camera Layout Detection Agent
- [Source: CLAUDE.md#Pipeline Stages] — Stage 5: Layout Detective
- [Source: CLAUDE.md#Hybrid Face Gate] — 6-component weighted duo score
- [Source: CLAUDE.md#Shot Classification] — classify_shot decision tree
