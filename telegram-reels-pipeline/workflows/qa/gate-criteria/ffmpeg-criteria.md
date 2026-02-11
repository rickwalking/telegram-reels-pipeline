# QA Gate: FFmpeg

## Evaluation Dimensions

### Dimension 1: Segment Encoding (weight: 30/100)
- **Pass**: All planned segments encoded successfully, files exist and are non-empty
- **Rework**: Some segments failed encoding but can be retried
- **Fail**: No segments encoded or all encoding attempts failed
- **Prescriptive fix template**: "Segment {segment_number} failed to encode. Re-encode with correct parameters. Check input path exists and crop filter is valid: {crop_filter}"

### Dimension 2: Output Dimensions (weight: 30/100)
- **Pass**: All encoded segments are exactly 1080x1920
- **Rework**: Segments have close but incorrect dimensions (e.g., 1078x1918)
- **Fail**: Segments have completely wrong dimensions (e.g., 1280x720)
- **Prescriptive fix template**: "Segment {n} is {actual_w}x{actual_h} instead of 1080x1920. Re-encode with correct scale filter: scale=1080:1920"

### Dimension 3: Codec Compliance (weight: 20/100)
- **Pass**: All segments use H.264 video codec and AAC audio codec
- **Rework**: Video codec is correct but audio codec differs
- **Fail**: Wrong video codec or no video stream
- **Prescriptive fix template**: "Segment {n} uses {actual_codec} instead of H.264. Re-encode with: -c:v libx264 -profile:v main -crf 23"

### Dimension 4: Audio Presence (weight: 20/100)
- **Pass**: All segments have audio tracks, audio is not silent
- **Rework**: Audio track present but unusually quiet or has minor sync issues
- **Fail**: No audio track in segments that should have audio
- **Prescriptive fix template**: "Segment {n} is missing audio track. Re-encode with audio: -c:a aac -b:a 128k"

## Scoring Rubric

- 90-100: Excellent — all segments encoded correctly, proper dimensions, codec, and audio
- 70-89: Good — all segments exist, minor codec or quality issues
- 50-69: Acceptable — most segments correct, one has issues
- 30-49: Poor — rework required, encoding failures or wrong dimensions
- 0-29: Fail — no valid encoded segments

## Output Schema Requirements

Output JSON (`encoding-plan.json`) must contain:
- `commands`: array of objects with `input`, `crop_filter`, `output`, `start_seconds`, `end_seconds`
- `segment_paths`: array of output file paths (all must exist after execution)
- `total_duration_seconds`: float (sum of all segment durations)
