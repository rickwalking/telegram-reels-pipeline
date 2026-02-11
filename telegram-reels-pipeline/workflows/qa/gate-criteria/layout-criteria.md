# QA Gate: Layout

## Evaluation Dimensions

### Dimension 1: Frame Classification (weight: 30/100)
- **Pass**: All frames classified with layout names matching KNOWN_LAYOUTS (snake_case: `side_by_side`, `speaker_focus`, `grid`), confidence >= 0.7
- **Rework**: Some frames have confidence between 0.5-0.69, or layout names not in KNOWN_LAYOUTS without escalation
- **Fail**: Frames with confidence < 0.5 and no escalation triggered, or invalid layout names
- **Prescriptive fix template**: "Frame at {timestamp}s has confidence {confidence}. Re-analyze or trigger escalation. Layout names must be snake_case matching KNOWN_LAYOUTS: side_by_side, speaker_focus, grid."

### Dimension 2: Transition Detection (weight: 20/100)
- **Pass**: Layout transitions correctly identified at boundary timestamps, segments properly split
- **Rework**: Transitions detected but boundary timestamps are imprecise (> 5s error)
- **Fail**: Obvious transitions missed (visible layout change between consecutive frames)
- **Prescriptive fix template**: "Layout transition missed between frames at {frame_a}s and {frame_b}s. These frames show different layouts ({layout_a} vs {layout_b}). Add a segment boundary."

### Dimension 3: Crop Region Validity (weight: 30/100)
- **Pass**: All crop regions within video bounds (x + width <= source_width, y + height <= source_height)
- **Rework**: Crop regions slightly exceed bounds (by < 10px)
- **Fail**: Crop regions significantly exceed video dimensions or are negative
- **Prescriptive fix template**: "Crop region for segment at {timestamp}s exceeds video bounds: x({x}) + width({width}) = {sum} > {source_width}. Adjust width to {corrected_width}."

### Dimension 4: Escalation Handling (weight: 20/100)
- **Pass**: Unknown layouts correctly escalated, or no unknown layouts found
- **Rework**: Unknown layout detected but escalation not triggered (confidence < 0.7 on non-KNOWN layout)
- **Fail**: Unknown layout silently assigned a KNOWN_LAYOUTS name (misclassification)
- **Prescriptive fix template**: "Layout '{name}' is not in KNOWN_LAYOUTS (side_by_side, speaker_focus, grid). Trigger escalation protocol for frame at {timestamp}s."

## Critical Validation

- Layout names MUST be snake_case: `side_by_side`, `speaker_focus`, `grid`
- Using kebab-case (e.g., `side-by-side`) causes `has_unknown_layouts()` to return True → false escalation
- Confidence values are float 0.0-1.0 (validated by LayoutClassification.__post_init__)

## Scoring Rubric

- 90-100: Excellent — all frames classified with high confidence, transitions detected, valid crops
- 70-89: Good — most frames classified, minor confidence issues
- 50-69: Acceptable — some low-confidence frames, may need escalation
- 30-49: Poor — rework required, significant classification or crop issues
- 0-29: Fail — unable to classify frames or crop regions invalid

## Output Schema Requirements

Output JSON must contain:
- `classifications`: array of objects with `timestamp` (float), `layout_name` (string, snake_case), `confidence` (float 0.0-1.0)
- `segments`: array of objects with `start_seconds`, `end_seconds`, `layout_name`, `crop_region` (object with x, y, width, height)
- `escalation_needed`: boolean
