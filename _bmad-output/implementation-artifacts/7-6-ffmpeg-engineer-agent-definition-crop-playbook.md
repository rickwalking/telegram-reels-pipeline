# Story 7.6: FFmpeg Engineer Agent Definition & Crop Playbook

Status: ready-for-dev

## Story

As a pipeline developer,
I want the FFmpeg Engineer Agent definition and supporting knowledge files written,
So that the FFmpeg stage can crop source video into vertical 9:16 segments and encode them for Instagram Reels.

## Acceptance Criteria

1. **Given** `agents/ffmpeg-engineer/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the FFMPEG_ENGINEER stage,
   **Then** it contains instructions for Claude to: plan FFmpeg commands for per-segment cropping, handle layout transitions, and encode at target specs (1080x1920, H.264).

2. **Given** the FFmpeg Engineer Agent executes with segment layouts and video path,
   **When** it produces output,
   **Then** it outputs: array of FFmpeg command specifications (input, crop filter, output), per-segment video file paths.

3. **Given** `agents/ffmpeg-engineer/crop-playbook.md` exists,
   **When** the agent plans crop operations,
   **Then** it follows the playbook: per-layout crop coordinates, aspect ratio math, safe-zone padding.

4. **Given** `agents/ffmpeg-engineer/encoding-params.md` exists,
   **When** the agent encodes video,
   **Then** it uses Pi-optimized encoding: H.264 Main profile, CRF 23, 1080x1920, AAC audio, hardware acceleration hints.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/ffmpeg-engineer/agent.md` (AC: #1, #2)
  - [ ] Agent persona: "FFmpeg Engineer" — the video processing specialist
  - [ ] Role: Plan and specify FFmpeg operations for cropping and encoding
  - [ ] Input contract: video path, array of SegmentLayout with CropRegion, moment start/end
  - [ ] Output contract: array of FFmpeg command specs, segment video paths
  - [ ] Behavioral rules: never exceed 3GB memory, split long segments, verify output dimensions match 1080x1920
  - [ ] Note: agent PLANS commands, FFmpegAdapter EXECUTES them via VideoProcessingPort

- [ ] Task 2: Write `agents/ffmpeg-engineer/crop-playbook.md` (AC: #3)
  - [ ] Per-layout crop coordinates for 1920x1080 source → 1080x1920 output (layout names use snake_case per `KNOWN_LAYOUTS`):
    - `side_by_side`: crop left speaker (x=0, w=960) or right (x=960, w=960), scale to 1080x1920
    - `speaker_focus`: crop around the primary speaker face region
    - `grid`: crop active speaker quadrant
    - Unknown layouts: use crop region from knowledge base (stored by LayoutEscalationHandler)
  - [ ] Safe-zone padding: ensure faces aren't clipped at edges
  - [ ] Transition handling: split segment at layout boundary, encode separately, concatenate

- [ ] Task 3: Write `agents/ffmpeg-engineer/encoding-params.md` (AC: #4)
  - [ ] Target specs: 1080x1920 (9:16), H.264 Main profile, CRF 23
  - [ ] Audio: AAC 128kbps, preserve original audio
  - [ ] Pi optimization: use `-preset medium` (balance speed/quality on ARM), avoid `-preset veryslow`
  - [ ] Memory constraint: peak memory < 3GB (NFR-P4)
  - [ ] Duration constraint: encoding time < 5 min for 90s segment (NFR-P2)
  - [ ] File size consideration: aim for < 50MB for Telegram inline delivery

## Dev Notes

### Output JSON Schema

```json
{
  "commands": [
    {
      "input": "/workspace/runs/XYZ/source.mp4",
      "crop_filter": "crop=960:1080:0:0,scale=1080:1920",
      "output": "/workspace/runs/XYZ/segment-001.mp4",
      "start_seconds": 1247.0,
      "end_seconds": 1270.0
    }
  ],
  "segment_paths": ["/workspace/runs/XYZ/segment-001.mp4", "..."],
  "total_duration_seconds": 78
}
```

### Agent Does NOT Execute FFmpeg

The agent PLANS the commands. The actual execution is done by:
- `FFmpegAdapter.crop_and_encode()` in `infrastructure/adapters/ffmpeg_adapter.py`
- Which calls `asyncio.create_subprocess_exec("ffmpeg", ...)`

The agent's job is to determine the correct crop filter, encoding params, and segment boundaries.

### PRD Functional Requirements

- FR12: Per-segment crop for vertical 9:16 at 1080x1920
- FR13: Handle layout transitions by splitting at boundaries
- NFR-P2: Encoding time <= 5 min on Pi ARM
- NFR-P4: Memory <= 3GB during encoding

### File Locations

```
telegram-reels-pipeline/agents/ffmpeg-engineer/agent.md          # Main agent definition
telegram-reels-pipeline/agents/ffmpeg-engineer/crop-playbook.md   # Per-layout crop coordinates
telegram-reels-pipeline/agents/ffmpeg-engineer/encoding-params.md # Encoding specifications
```

### References

- [Source: prd.md#FR12-FR13, NFR-P2, NFR-P4] — Video processing requirements
- [Source: domain/models.py#CropRegion, SegmentLayout] — Domain models
- [Source: infrastructure/adapters/ffmpeg_adapter.py] — FFmpegAdapter implementation

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
