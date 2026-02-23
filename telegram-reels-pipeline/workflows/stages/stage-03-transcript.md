# Stage 3: Transcript Analysis

## Objective

Analyze the full episode transcript to identify and select the best 60-90 second moment for an Instagram Reel.

## Inputs

- **research-output.json**: Contains `transcript_text`, `episode_summary`, `key_themes`, `speakers_identified`
- **topic_focus** (optional): User-specified topic from elicitation context
- **moments_requested** (optional): Number of narrative moments (1-5). Default: 1
- **target_duration_seconds** (optional): Target total output duration. Default: 90

## Expected Outputs

- **moment-selection.json**: Selected moment with timestamps and rationale

```json
{
  "start_seconds": 1247.0,
  "end_seconds": 1325.0,
  "transcript_text": "The selected transcript portion...",
  "rationale": "Why this moment was selected...",
  "topic_match_score": 0.85,
  "alternative_moments": [...]
}
```

**CRITICAL field names**: Use `transcript_text` (NOT `text`). Use `topic_match_score` as float 0.0-1.0 (NOT 0-100).

## Instructions

1. **Read the full transcript** from research-output.json.
2. **Check for multi-moment mode** — if `moments_requested >= 2` in the elicitation context, activate multi-moment selection.
3. **Identify candidate moments** — scan for narrative arcs, emotional peaks, quotable statements.
4. **Score each candidate** using the four-dimension rubric (narrative, emotional, quotable, relevance). See `moment-selection-criteria.md`.
5. **Apply topic_focus weighting** — if user specified a topic, prioritize matching segments.
6. **Select moment(s)**:
   - **Single-moment mode** (`moments_requested = 1` or absent): select the highest-scoring candidate within 30-120s.
   - **Multi-moment mode** (`moments_requested >= 2`): select `moments_requested` complementary moments with narrative roles. Each moment >= 15s. Total within ±20% of `target_duration_seconds`. Minimum 30s gap between moments. Assign roles: intro, buildup, core, reaction, conclusion (exactly one core, no duplicates).
7. **Set clean boundaries** — ensure start/end land on complete sentences for each moment.
8. **Include 2-3 alternatives** — backup moments ranked by score.
9. **Output valid JSON** as `moment-selection.json`. For multi-moment, include `moments[]` array alongside top-level fields.

## Constraints

- Duration: 30-120 seconds (60-90 preferred). Enforced by MomentSelection dataclass.
- `topic_match_score`: float 0.0-1.0 (validated by `__post_init__`)
- `transcript_text`: the selected portion of transcript (NOT the full transcript)
- Rationale must be substantive (> 50 words)
- Never select intro (first 120s) or outro (last 120s) of the episode
- Clean sentence boundaries — never cut mid-word

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/transcript-criteria.md`

## Escalation Rules

- Transcript too short (< 5 min total): select best available, flag in rationale
- No segment matches topic_focus: select most engaging regardless, set low topic_match_score
- All candidates score below 50/100: select best available, flag for QA review

## Prior Artifact Dependencies

- `research-output.json` from Stage 2 (Research) — provides transcript, themes, speakers
- `router-output.json` from Stage 1 (Router) — provides topic_focus via elicitation_context
