# Story 7.3: Transcript Agent Definition & Moment Selection

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Transcript Agent definition and moment selection criteria written,
So that the Transcript stage can analyze full episode transcripts and select the best 60-90 second moment for a Reel.

## Acceptance Criteria

1. **Given** `agents/transcript/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the TRANSCRIPT stage,
   **Then** it contains instructions for Claude to: analyze the transcript, score candidate moments, select the best segment, and output a MomentSelection.

2. **Given** the Transcript Agent executes with episode context and transcript,
   **When** it selects a moment,
   **Then** it outputs a JSON matching MomentSelection: `start_seconds`, `end_seconds`, `transcript_text`, `rationale`, `topic_match_score`,
   **And** the segment duration is between 30-120 seconds (60-90 preferred).

3. **Given** a user specified a `topic_focus` during elicitation,
   **When** the Transcript Agent selects a moment,
   **Then** it prioritizes segments matching the topic focus,
   **And** reports the `topic_match_score` as a float from 0.0-1.0 (NOT 0-100).

4. **Given** `agents/transcript/moment-selection-criteria.md` exists,
   **When** the Transcript Agent evaluates candidates,
   **Then** it applies: narrative structure score, emotional peak detection, quotable statement density, and topic relevance.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/transcript/agent.md` (AC: #1, #2, #3)
  - [ ] Agent persona: "Transcript Analyst" — the moment hunter
  - [ ] Role: Analyze full transcript, identify highest-value moments, select best segment
  - [ ] Input contract: transcript_text, episode_summary, key_themes, topic_focus (optional)
  - [ ] Output contract: JSON with `start_seconds`, `end_seconds`, `transcript_text` (selected transcript portion — MUST use `transcript_text` not `text`), `rationale`, `topic_match_score` (float 0.0-1.0, NOT 0-100), `alternative_moments` (top 3)
  - [ ] Behavioral rules: prefer 60-90s segments, never select intro/outro, weight topic_focus heavily when provided
  - [ ] Reference moment-selection-criteria.md for scoring rubric

- [ ] Task 2: Write `agents/transcript/moment-selection-criteria.md` (AC: #4)
  - [ ] Scoring dimensions (each 0-25, total 0-100):
    - Narrative structure: complete thought arc (setup → development → insight)
    - Emotional peak: intensity of discussion, surprise, humor, controversy
    - Quotable density: memorable one-liners, shareable insights per minute
    - Topic relevance: match to episode themes and user's topic_focus
  - [ ] Segment constraints: 30-120 seconds, clean sentence boundaries, avoid mid-word cuts
  - [ ] Disqualification rules: ads/sponsors, meta-commentary ("welcome to the show"), pure filler

## Dev Notes

### Output JSON Schema

```json
{
  "start_seconds": 1247.0,
  "end_seconds": 1325.0,
  "transcript_text": "Selected transcript text...",
  "rationale": "Strong emotional peak discussing AI risks with quotable insights",
  "topic_match_score": 0.85,
  "alternative_moments": [
    {"start_seconds": 2100.0, "end_seconds": 2175.0, "score": 0.72, "brief": "..."},
    {"start_seconds": 890.0, "end_seconds": 962.0, "score": 0.68, "brief": "..."}
  ]
}
```

### Integration Points

- **Input**: Research stage artifacts (transcript, metadata, themes) via `prior_artifacts`
- **Output**: Written as `moment-selection.json` in workspace
- **Downstream**: Layout Detective uses timestamps to extract frames; FFmpeg uses start/end for cropping
- **Elicitation**: `topic_focus` from Router stage via `elicitation_context`

### Domain Model Alignment

Output must map to `MomentSelection` frozen dataclass (from `domain/models.py:162`):
- `start_seconds: float`
- `end_seconds: float`
- `transcript_text: str` (NOT `text` — field name is `transcript_text`)
- `rationale: str`
- `topic_match_score: float` (range 0.0-1.0, NOT 0-100; validated in `__post_init__`)

Duration validation: `30.0 <= (end - start) <= 120.0` (enforced by dataclass)

### PRD Functional Requirements

- FR7: Analyze transcript — narrative structure, emotional peaks, quotable density
- FR8: Focus on user-specified topic when provided
- FR9: Select 60-90 second segment

### File Locations

```
telegram-reels-pipeline/agents/transcript/agent.md                      # Main agent definition
telegram-reels-pipeline/agents/transcript/moment-selection-criteria.md   # Scoring rubric
```

### References

- [Source: prd.md#FR7-FR9] — Moment selection requirements
- [Source: domain/models.py#MomentSelection] — MomentSelection dataclass
- [Source: pipeline_runner.py#_STAGE_DISPATCH] — Transcript stage mapping

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
