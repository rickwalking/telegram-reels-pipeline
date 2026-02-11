# Story 7.7: Assembly Agent Definition

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Assembly (QA) Agent definition written,
So that the Assembly stage can combine encoded video segments into the final Reel with proper transitions and quality validation.

## Acceptance Criteria

1. **Given** `agents/qa/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the ASSEMBLY stage,
   **Then** it contains instructions for Claude to: verify all segments are encoded, plan the concatenation order, specify any transitions, and validate the final output.

2. **Given** the Assembly Agent executes with encoded segment paths,
   **When** it produces output,
   **Then** it outputs: concatenation plan (ordered segment list), transition specs (if any), final output path, and a quality checklist verification.

3. **Given** multiple segments need concatenation,
   **When** the Assembly Agent plans the assembly,
   **Then** segments are ordered by timestamp, transitions are smooth (crossfade or cut), and the final video maintains 1080x1920 at consistent quality.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/qa/agent.md` (AC: #1, #2, #3)
  - [ ] Agent persona: "Assembly Engineer" — the final quality gatekeeper
  - [ ] Role: Plan final video assembly from encoded segments, verify quality
  - [ ] Input contract: array of segment video paths (from FFmpeg stage), moment metadata
  - [ ] Output contract: JSON with `concatenation_order` (array of paths), `transitions` (array of type + duration), `final_output_path`, `quality_checks` (dimensions, duration, file_size)
  - [ ] Behavioral rules: verify all segments exist before assembly, validate total duration matches moment selection, fail if any segment is corrupt or wrong dimensions
  - [ ] Quality validation: final video is 1080x1920, duration within 5% of expected, file size < 50MB for Telegram

## Dev Notes

### Output JSON Schema

```json
{
  "concatenation_order": [
    "/workspace/runs/XYZ/segment-001.mp4",
    "/workspace/runs/XYZ/segment-002.mp4"
  ],
  "transitions": [
    {"type": "cut", "at_seconds": 23.0}
  ],
  "final_output_path": "/workspace/runs/XYZ/final-reel.mp4",
  "quality_checks": {
    "dimensions": "1080x1920",
    "duration_seconds": 78,
    "file_size_mb": 42,
    "codec": "h264",
    "audio_codec": "aac"
  }
}
```

### Agent Directory Note

The Assembly agent lives in `agents/qa/` (not `agents/assembly/`) because the stage dispatch table maps ASSEMBLY → `qa` directory. This is an existing convention from the pipeline_runner.py:
```python
PipelineStage.ASSEMBLY: ("stage-07-assembly.md", "qa", "assembly"),
```

### Integration Points

- **Input**: Encoded segment paths from FFmpeg Engineer stage
- **Output**: Final reel video path for Delivery stage
- **Tool**: ReelAssembler adapter in `infrastructure/adapters/reel_assembler.py`

### File Locations

```
telegram-reels-pipeline/agents/qa/agent.md   # Assembly/QA agent definition
```

### References

- [Source: pipeline_runner.py#_STAGE_DISPATCH] — ASSEMBLY maps to "qa" directory
- [Source: infrastructure/adapters/reel_assembler.py] — ReelAssembler implementation
- [Source: prd.md] — Final Reel delivery requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
