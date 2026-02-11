# Story 8.1: Stage Workflow Files

Status: ready-for-dev

## Story

As a pipeline developer,
I want all 8 stage workflow files written,
So that PipelineRunner can load stage instructions for each pipeline step and PromptBuilder can construct complete agent prompts.

## Acceptance Criteria

1. **Given** `workflows/stages/stage-01-router.md` through `stage-08-delivery.md` exist and are non-empty,
   **When** PipelineRunner builds an AgentRequest for any stage,
   **Then** `_build_request()` loads the step file successfully via `self._workflows_dir / "stages" / step_file_name`.

2. **Given** each stage file contains structured instructions,
   **When** PromptBuilder combines it with the agent definition,
   **Then** the resulting prompt gives Claude: the objective of this stage, expected inputs and outputs, constraints, quality criteria reference, and escalation rules.

3. **Given** stage files reference prior stage artifacts,
   **When** stages execute in sequence,
   **Then** each stage file documents exactly which prior artifacts it needs and what format they should be in.

4. **Given** the 8 stage files exist,
   **When** I validate them against PipelineRunner's `_STAGE_DISPATCH` table,
   **Then** every filename in the dispatch table has a corresponding file in `workflows/stages/`,
   **And** 7 of 8 files are loaded at runtime (stage-01 through stage-07), while stage-08-delivery.md is documentation-only (see note below).

## Tasks / Subtasks

- [ ] Task 1: Write `stage-01-router.md` (AC: #1, #2, #3)
  - [ ] Objective: Parse user input, extract URL, determine elicitation needs
  - [ ] Inputs: Raw Telegram message text
  - [ ] Outputs: `router-output.json` with url, topic_focus, revision routing
  - [ ] Constraints: max 2 elicitation questions, 60s timeout
  - [ ] QA gate: router criteria

- [ ] Task 2: Write `stage-02-research.md` (AC: #1, #2, #3)
  - [ ] Objective: Download video metadata and subtitles, build episode context
  - [ ] Inputs: URL from router output
  - [ ] Outputs: `research-output.json` with metadata, transcript, themes, speakers
  - [ ] Constraints: retry downloads 3x with backoff
  - [ ] QA gate: research criteria

- [ ] Task 3: Write `stage-03-transcript.md` (AC: #1, #2, #3)
  - [ ] Objective: Analyze transcript, select best 60-90s moment
  - [ ] Inputs: research-output.json (transcript, themes, topic_focus)
  - [ ] Outputs: `moment-selection.json` with timestamps, text, rationale, score
  - [ ] Constraints: 30-120s duration, clean sentence boundaries
  - [ ] QA gate: transcript criteria

- [ ] Task 4: Write `stage-04-content.md` (AC: #1, #2, #3)
  - [ ] Objective: Generate Instagram content package
  - [ ] Inputs: moment-selection.json, research-output.json
  - [ ] Outputs: `content.json` with descriptions, hashtags, music, mood
  - [ ] Constraints: 3 descriptions, 10-15 hashtags, Instagram char limits
  - [ ] QA gate: content criteria

- [ ] Task 5: Write `stage-05-layout-detective.md` (AC: #1, #2, #3)
  - [ ] Objective: Extract frames, classify layouts, plan crop regions
  - [ ] Inputs: video file, moment timestamps
  - [ ] Outputs: `layout-analysis.json` with classifications and segment layouts
  - [ ] Constraints: frames every 5s, confidence threshold 0.7
  - [ ] QA gate: layout criteria
  - [ ] Escalation: unknown layout → user notification

- [ ] Task 6: Write `stage-06-ffmpeg-engineer.md` (AC: #1, #2, #3)
  - [ ] Objective: Plan FFmpeg crop and encode operations
  - [ ] Inputs: layout-analysis.json, video file, moment timestamps
  - [ ] Outputs: encoded segment files (.mp4), `encoding-plan.json`
  - [ ] Constraints: 1080x1920, H.264, <3GB memory, <5min encode time
  - [ ] QA gate: ffmpeg criteria

- [ ] Task 7: Write `stage-07-assembly.md` (AC: #1, #2, #3)
  - [ ] Objective: Concatenate segments into final Reel
  - [ ] Inputs: encoded segment paths
  - [ ] Outputs: `final-reel.mp4`, `assembly-report.json`
  - [ ] Constraints: maintain dimensions, verify duration, check file size
  - [ ] QA gate: assembly criteria

- [ ] Task 8: Write `stage-08-delivery.md` (AC: #1, #2, #3)
  - [ ] Objective: Deliver final Reel and content to user
  - [ ] Inputs: final-reel.mp4, content.json
  - [ ] Outputs: delivery confirmation, revision prompt sent
  - [ ] Constraints: <50MB inline, else Google Drive
  - [ ] No QA gate (final stage)
  - [ ] NOTE: This file is documentation-only for MVP — PipelineRunner bypasses agent execution for DELIVERY (line 147) and calls DeliveryHandler directly. See Story 7.8 dev notes.

- [ ] Task 9: Validate dispatch table alignment (AC: #4)
  - [ ] Verify all 8 filenames match `_STAGE_DISPATCH` in pipeline_runner.py
  - [ ] Note: 7 of 8 are loaded at runtime. stage-08-delivery.md exists for completeness but is not loaded by `_build_request()` because DELIVERY bypasses StageRunner.

## Dev Notes

### Stage File Template

Each stage file should follow this structure:

```markdown
# Stage X: [Stage Name]

## Objective
[What this stage accomplishes]

## Inputs
- [Input 1]: [description, format, source]

## Expected Outputs
- [Output 1]: [description, format, filename]

## Instructions
[Step-by-step instructions for Claude]

## Constraints
- [Constraint 1]

## Quality Criteria Reference
See: workflows/qa/gate-criteria/{gate}-criteria.md

## Escalation Rules
[When and how to escalate]

## Prior Artifact Dependencies
[Explicit list of what prior stages must produce]
```

### IMPORTANT: Delivery Stage Bypass

PipelineRunner at line 147 handles DELIVERY specially — it calls `_execute_delivery()` directly instead of going through `_build_request()` → StageRunner. This means `stage-08-delivery.md` is never loaded at runtime. It should still be written for documentation completeness, but be aware it has no runtime effect.

The 7 runtime-loaded stage files are: stage-01 through stage-07.

### PipelineRunner Stage Dispatch (from pipeline_runner.py)

```python
_STAGE_DISPATCH = {
    ROUTER:           ("stage-01-router.md",           "router",           "router"),
    RESEARCH:         ("stage-02-research.md",         "research",         "research"),
    TRANSCRIPT:       ("stage-03-transcript.md",       "transcript",       "transcript"),
    CONTENT:          ("stage-04-content.md",          "content-creator",  "content"),
    LAYOUT_DETECTIVE: ("stage-05-layout-detective.md", "layout-detective", "layout"),
    FFMPEG_ENGINEER:  ("stage-06-ffmpeg-engineer.md",  "ffmpeg-engineer",  "ffmpeg"),
    ASSEMBLY:         ("stage-07-assembly.md",         "qa",               "assembly"),
    DELIVERY:         ("stage-08-delivery.md",         "delivery",         ""),
}
```

### File Locations

```
telegram-reels-pipeline/workflows/stages/stage-01-router.md
telegram-reels-pipeline/workflows/stages/stage-02-research.md
telegram-reels-pipeline/workflows/stages/stage-03-transcript.md
telegram-reels-pipeline/workflows/stages/stage-04-content.md
telegram-reels-pipeline/workflows/stages/stage-05-layout-detective.md
telegram-reels-pipeline/workflows/stages/stage-06-ffmpeg-engineer.md
telegram-reels-pipeline/workflows/stages/stage-07-assembly.md
telegram-reels-pipeline/workflows/stages/stage-08-delivery.md
```

### References

- [Source: pipeline_runner.py#_STAGE_DISPATCH] — Stage dispatch table
- [Source: prompt_builder.py] — How stage files are read and combined with agent defs
- [Source: retrospective-epics-1-6.md#Critical Gap 2] — Empty stage files
- [Source: prd.md] — Full pipeline flow requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
