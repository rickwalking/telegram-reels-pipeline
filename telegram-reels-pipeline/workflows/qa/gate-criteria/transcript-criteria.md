# QA Gate: Transcript

## Evaluation Dimensions

### Dimension 1: Duration Compliance (weight: 30/100)
- **Pass**: Segment duration between 30-120 seconds, ideally 60-90 seconds
- **Rework**: Duration is outside 30-120s range but within 20-150s (close to acceptable)
- **Fail**: Duration is < 20s or > 150s, or start_seconds >= end_seconds
- **Prescriptive fix template**: "Adjust segment boundaries to fit 30-120s range. Current duration {duration}s exceeds {limit}s max. Trim from the {suggestion} of the segment."

### Dimension 2: Boundary Quality (weight: 25/100)
- **Pass**: Segment starts and ends on complete sentences, no mid-word cuts
- **Rework**: Segment cuts mid-sentence at start or end
- **Fail**: Segment starts or ends mid-word, or boundaries are nonsensical
- **Prescriptive fix template**: "Segment cuts mid-sentence at {position}. Adjust {boundary}_seconds by {direction} {seconds}s to land on a complete sentence boundary."

### Dimension 3: Topic Match (weight: 25/100)
- **Pass**: `topic_match_score` >= 0.6 (float 0.0-1.0, NOT 0-100), segment clearly relates to topic_focus or strongest episode theme
- **Rework**: `topic_match_score` between 0.3-0.59, tangentially related
- **Fail**: `topic_match_score` < 0.3, segment is off-topic
- **Prescriptive fix template**: "Current topic_match_score is {score}. Select a segment that better matches topic '{topic_focus}'. Check transcript around timestamps {suggested_range} for better matches."

### Dimension 4: Rationale Quality (weight: 20/100)
- **Pass**: Rationale is > 50 words, references scoring dimensions, explains why this moment is engaging
- **Rework**: Rationale exists but is < 50 words or is generic
- **Fail**: No rationale or rationale is a single sentence
- **Prescriptive fix template**: "Expand rationale to > 50 words. Explain which scoring dimensions (narrative, emotional, quotable, relevance) make this moment strong."

## Critical Field Validation

- **Field name**: `transcript_text` (NOT `text`) — must match MomentSelection dataclass
- **Score range**: `topic_match_score` is float 0.0-1.0 (NOT 0-100) — validated by `__post_init__`
- **Duration**: validated by MomentSelection: `30.0 <= (end - start) <= 120.0`

## Scoring Rubric

- 90-100: Excellent — perfect duration, clean boundaries, high relevance, detailed rationale
- 70-89: Good — within range, minor boundary issues, decent relevance
- 50-69: Acceptable — borderline duration or relevance, may trigger rework
- 30-49: Poor — rework required, duration or relevance issues
- 0-29: Fail — fundamentally wrong selection

## Output Schema Requirements

Output JSON must contain:
- `start_seconds`: float (>= 0)
- `end_seconds`: float (> start_seconds)
- `transcript_text`: non-empty string (the selected portion)
- `rationale`: string (> 50 words)
- `topic_match_score`: float 0.0-1.0
- `alternative_moments`: array of 2-3 backup candidates
