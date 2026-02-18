# QA Gate: Router

## Evaluation Dimensions

### Dimension 1: URL Extraction (weight: 30/100)
- **Pass**: Valid YouTube URL extracted and present in output JSON
- **Rework**: URL field is present but malformed (not a valid YouTube URL pattern)
- **Fail**: No URL field in output, or output is not valid JSON
- **Prescriptive fix template**: "Ensure output contains 'url' field with a valid YouTube URL matching pattern: youtube.com/watch?v= or youtu.be/"

### Dimension 2: Output Structure (weight: 25/100)
- **Pass**: Output JSON is valid and contains all required fields (url, topic_focus, duration_preference, framing_style)
- **Rework**: JSON is valid but missing optional fields or has extra unexpected fields
- **Fail**: Output is not valid JSON
- **Prescriptive fix template**: "Output must be valid JSON with required fields: url, topic_focus, duration_preference, framing_style. Current output is missing: {missing_fields}"

### Dimension 3: Elicitation Quality (weight: 20/100)
- **Pass**: 0-2 relevant elicitation questions, or smart defaults applied correctly
- **Rework**: More than 2 questions asked, or questions are irrelevant to the content
- **Fail**: Questions are confusing, contradictory, or block pipeline progress
- **Prescriptive fix template**: "Reduce elicitation questions to maximum 2. Current count: {count}. Remove: {least_relevant_question}"

### Dimension 4: Revision Classification (weight: 25/100)
- **Pass**: Revision type correctly classified against RevisionType enum when applicable
- **Rework**: Revision detected but misclassified (wrong RevisionType)
- **Fail**: Revision request ignored entirely or crashes the router
- **Prescriptive fix template**: "Message '{user_message}' should be classified as {correct_type}, not {current_type}. See revision-interpretation.md mapping table."

## Scoring Rubric

- 90-100: Excellent — all dimensions pass, clean JSON, appropriate defaults
- 70-89: Good — minor issues (extra fields, slightly off defaults), passes
- 50-69: Acceptable — URL extracted but structure needs cleanup
- 30-49: Poor — rework required, missing critical fields
- 0-29: Fail — no valid output or fundamentally broken

## Output Schema Requirements

Output JSON must contain:
- `url`: string or null (valid YouTube URL for new requests)
- `topic_focus`: string or null
- `duration_preference`: integer (30-120)
- `framing_style`: string (one of: `default`, `split_horizontal`, `pip`, `auto`)
- `revision_type`: string or null (one of: `extend_moment`, `fix_framing`, `different_moment`, `add_context` — lowercase enum values)
- `routing_target`: string or null
- `elicitation_questions`: array (0-2 items)
