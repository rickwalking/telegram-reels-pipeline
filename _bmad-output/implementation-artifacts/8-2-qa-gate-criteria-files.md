# Story 8.2: QA Gate Criteria Files

Status: ready-for-dev

## Story

As a pipeline developer,
I want all 7 QA gate criteria files written,
So that the ReflectionLoop can evaluate stage outputs against defined quality standards and provide prescriptive feedback for rework.

## Acceptance Criteria

1. **Given** `workflows/qa/gate-criteria/{gate}-criteria.md` exists for each of the 7 gated stages,
   **When** PipelineRunner calls `_load_gate_criteria(gate_name)`,
   **Then** the criteria file is loaded successfully and returns non-empty content.

2. **Given** each gate criteria file contains evaluation dimensions,
   **When** the ReflectionLoop evaluates an agent's output,
   **Then** the QA model can score the output against specific, measurable criteria,
   **And** return a QACritique with `decision` (PASS/REWORK/FAIL), `score` (0-100), `blockers`, and `prescriptive_fixes`.

3. **Given** a QA gate returns REWORK,
   **When** prescriptive feedback is generated,
   **Then** the feedback references specific criteria from the gate file that were not met,
   **And** provides exact fix instructions the agent can act on.

4. **Given** the 7 gate criteria files exist,
   **When** I validate them against PipelineRunner's dispatch table,
   **Then** every `gate_name` in `_STAGE_DISPATCH` (except DELIVERY which has no gate) has a corresponding criteria file.

## Tasks / Subtasks

- [ ] Task 1: Write `router-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: valid YouTube URL extracted, elicitation questions relevant, revision type correctly classified
  - [ ] Pass threshold: URL is valid, output JSON parseable
  - [ ] Rework triggers: malformed URL, too many questions (>2), missing required fields
  - [ ] Prescriptive fixes: "Ensure output contains 'url' field with valid YouTube URL"

- [ ] Task 2: Write `research-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: metadata complete, transcript non-empty, themes identified, summary coherent
  - [ ] Pass threshold: all required metadata fields present, transcript length > 100 words
  - [ ] Rework triggers: missing metadata fields, empty transcript, no themes identified
  - [ ] Prescriptive fixes: "Re-download subtitles and extract at least 3 key themes"

- [ ] Task 3: Write `transcript-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: segment within 30-120s, clean boundaries, high topic_match_score, rationale provided
  - [ ] Pass threshold: duration 30-120s, topic_match_score >= 0.6 (float 0.0-1.0, NOT 0-100), rationale > 50 words
  - [ ] Field name: `transcript_text` (NOT `text`) — must match MomentSelection dataclass
  - [ ] Rework triggers: out-of-range duration, low topic match, cuts mid-sentence
  - [ ] Prescriptive fixes: "Adjust segment boundaries to complete sentences. Current duration 150s exceeds 120s max."

- [ ] Task 4: Write `content-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: exactly 3 descriptions, 10-15 hashtags, descriptions under 2200 chars, `music_suggestion` (singular string, non-empty) present, `mood_category` present
  - [ ] Pass threshold: all counts correct, format valid, JSON parseable by `content_parser.py`
  - [ ] Rework triggers: wrong number of descriptions, hashtags missing #, descriptions too long, `music_suggestion` empty
  - [ ] Prescriptive fixes: "Add 2 more hashtags to reach minimum of 10. Current count: 8."

- [ ] Task 5: Write `layout-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: all frames classified with snake_case layout names (must match `KNOWN_LAYOUTS`: `side_by_side`, `speaker_focus`, `grid`), confidence >= 0.7 (float 0.0-1.0), transitions detected, crop regions valid
  - [ ] Pass threshold: no unclassified frames (or escalation triggered), crop regions within video bounds
  - [ ] Rework triggers: frames with confidence < 0.5, layout names not in KNOWN_LAYOUTS (triggers escalation), crop regions exceeding video dimensions
  - [ ] Prescriptive fixes: "Frame at 1252s has confidence 0.45. Re-analyze or trigger escalation."

- [ ] Task 6: Write `ffmpeg-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: all segments encoded, dimensions 1080x1920, codec H.264, audio present, file not corrupt
  - [ ] Pass threshold: all segments exist, correct dimensions, playable
  - [ ] Rework triggers: wrong dimensions, missing audio, encoding errors
  - [ ] Prescriptive fixes: "Segment 2 is 1280x720 instead of 1080x1920. Re-encode with correct scale filter."

- [ ] Task 7: Write `assembly-criteria.md` (AC: #1, #2, #3)
  - [ ] Criteria: final video exists, dimensions 1080x1920, duration within 5% of expected, audio synced
  - [ ] Pass threshold: file exists, correct dimensions, duration acceptable
  - [ ] Rework triggers: duration mismatch >10%, corrupt output, audio desync
  - [ ] Prescriptive fixes: "Final duration 45s vs expected 78s. Check concatenation order — segment 2 may be missing."

- [ ] Task 8: Validate gate name alignment (AC: #4)
  - [ ] Verify: router, research, transcript, content, layout, ffmpeg, assembly all have criteria files

## Dev Notes

### Gate Criteria Template

Each criteria file should follow this structure:

```markdown
# QA Gate: [Gate Name]

## Evaluation Dimensions

### Dimension 1: [Name] (weight: X/100)
- **Pass**: [condition]
- **Rework**: [condition with specific trigger]
- **Fail**: [condition — unrecoverable]
- **Prescriptive fix template**: "[exact instruction for agent]"

## Scoring Rubric
- 90-100: Excellent — all dimensions pass with high quality
- 70-89: Good — minor issues, passes
- 50-69: Acceptable — borderline, may trigger rework
- 30-49: Poor — rework required
- 0-29: Fail — fundamental issues, may escalate

## Output Schema Requirements
[What fields the output JSON must contain]
```

### PipelineRunner Gate Loading (from pipeline_runner.py)

```python
async def _load_gate_criteria(self, gate_name: str) -> str:
    criteria_path = self._workflows_dir / "qa" / "gate-criteria" / f"{gate_name}-criteria.md"
    # Returns empty string if file not found (warning logged)
```

### Gate Names from Dispatch Table

```
router, research, transcript, content, layout, ffmpeg, assembly
```

Note: DELIVERY has no gate (empty string in dispatch table).

### File Locations

```
telegram-reels-pipeline/workflows/qa/gate-criteria/router-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/research-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/transcript-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/content-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/layout-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/ffmpeg-criteria.md
telegram-reels-pipeline/workflows/qa/gate-criteria/assembly-criteria.md
```

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 3] — Empty gate criteria
- [Source: pipeline_runner.py#_load_gate_criteria] — How criteria files are loaded
- [Source: reflection_loop.py] — ReflectionLoop QA evaluation
- [Source: domain/models.py#QACritique] — QACritique schema (decision, score, blockers, prescriptive_fixes)
- [Source: prd.md#FR20-FR23] — QA gate requirements

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
