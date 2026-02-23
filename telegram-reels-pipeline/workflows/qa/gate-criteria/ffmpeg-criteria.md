# QA Gate: FFmpeg

## Evaluation Dimensions

### Dimension 1: Segment Encoding (weight: 13/100)
- **Pass**: All planned segments encoded successfully, files exist and are non-empty
- **Rework**: Some segments failed encoding but can be retried
- **Fail**: No segments encoded or all encoding attempts failed
- **Prescriptive fix template**: "Segment {segment_number} failed to encode. Re-encode with correct parameters. Check input path exists and crop filter is valid: {crop_filter}"

### Dimension 2: Output Dimensions and SAR (weight: 13/100)
- **Pass**: All encoded segments are exactly 1080x1920 with SAR 1:1 (square pixels). Verify with `ffprobe -show_entries stream=width,height,sample_aspect_ratio`.
- **Pass (split-screen)**: For `framing_style=split_horizontal`, output is 1080x1920 composed of two 1080x960 halves via `vstack`, SAR 1:1. Verify each half contains a face.
- **Pass (PiP)**: For `framing_style=pip`, output is 1080x1920 with a 280x500 overlay positioned within frame bounds, SAR 1:1. Verify main frame contains active speaker face and overlay contains inactive speaker.
- **Rework**: Dimensions correct but SAR is not 1:1 (e.g., SAR 472:243). This means `setsar=1` was missing from the filter chain. Instagram will crop/misframe the video on upload.
- **Fail**: Segments have completely wrong dimensions (e.g., 1280x720)
- **Prescriptive fix template**: "Segment {n} has SAR {actual_sar} instead of 1:1. Append setsar=1 to the filter chain. For any crop width: crop={W}:1080:{x}:0,scale=1080:1920:flags=lanczos,setsar=1"

### Dimension 3: Codec Compliance (weight: 9/100)
- **Pass**: All segments use H.264 video codec and AAC audio codec
- **Rework**: Video codec is correct but audio codec differs
- **Fail**: Wrong video codec or no video stream
- **Prescriptive fix template**: "Segment {n} uses {actual_codec} instead of H.264. Re-encode with: -c:v libx264 -profile:v main -crf 23"

### Dimension 4: Audio Presence (weight: 9/100)
- **Pass**: All segments have audio tracks, audio is not silent
- **Rework**: Audio track present but unusually quiet or has minor sync issues
- **Fail**: No audio track in segments that should have audio
- **Prescriptive fix template**: "Segment {n} is missing audio track. Re-encode with audio: -c:a aac -b:a 128k"

### Dimension 5: Face Validation (weight: 18/100)
- **Pass**: All segments reference `face-position-map.json`; crop regions overlap with detected faces at segment timestamps; `encoding-plan.json` includes `validation` results per command with `face_in_crop: true`
- **Rework**: Most segments valid but one has marginal result (face near crop edge, < 40px padding)
- **Rework** (people cut off): If `face-position-map.json` shows 2+ faces at any frame timestamp within a segment's time range AND those faces fit within one crop (`speaker_span <= crop_width - 80px`), but the segment's crop region only covers 1 face — the crop is cutting someone off. Split the segment at the camera transition point and apply appropriate crops for each sub-segment. This rule does NOT apply when speakers are too far apart to fit in a single crop (legitimate per-speaker sub-segments).
- **Fail**: Any segment has no face in its crop region at the segment's timestamps and was not flagged for rework. Any segment shows 2+ faces that fit in one crop but crops all but one face out for more than 5 seconds (matching the minimum hold rule).
- **Prescriptive fix template** (no face): "Segment {n} crop at x={x}, w={w} has no face overlap at t={timestamp}s. Nearest face is at x={face_x}. Adjust crop to center on face: x = {corrected_x}."
- **Prescriptive fix template** (people cut off): "Segment {n} crop at x={x}, w={w} covers only 1 of {face_count} faces at t={timestamp}s. Faces fit in one crop (span={span}px < crop_width-80={limit}px). Split segment at camera transition and use both-visible crop for the wide-shot portion."

### Dimension 6: Output Quality (weight: 13/100)
- **Pass**: All segments have upscale factor <= 1.5 AND (sharpness ratio >= 0.6 when baseline available); `encoding-plan.json` includes `quality` results per command
- **Rework**: Any segment has upscale factor 1.5-2.0 OR sharpness ratio between 0.4-0.6
- **Fail**: Any segment has upscale factor > 2.0, OR sharpness ratio < 0.4
- **Prescriptive fix template**: "Segment {n} upscale factor is {factor}x (crop_width={crop_w}, target=1080). Widen crop to reduce upscale factor below 1.5x. Use: crop={wider_W}:1080:{adjusted_x}:0,scale=1080:1920:flags=lanczos,setsar=1"
- **Visual Consistency Check**: Flag if sharpness variance between adjacent segments > 30%. Fix: "Adjacent segments {n} and {n+1} have sharpness {s1} vs {s2} (>30% variance). Consider matching encoding approach (both pillarbox or both full-bleed)."
- **Scaler Check**: All segments must use `flags=lanczos`. Fix: "Segment {n} uses default bicubic scaler. Re-encode with: scale=1080:1920:flags=lanczos"

### Dimension 7: Duration Accuracy (weight: 15/100)
- **Pass**: Total encoded duration matches moment selection range (within 1s tolerance)
- **Rework**: Duration off by 1-3 seconds
- **Fail**: Duration off by more than 3 seconds, or segments overlap/gap
- **Boundary trim exemption**: Gaps between adjacent segments are permitted when `boundary_validation` on either segment shows `start_trimmed: true` or `end_trimmed: true`. These gaps (up to 2.0s each) contain ambiguous camera transition frames and are intentionally excluded. Subtract trimmed seconds from the expected duration before checking tolerance.
- **Prescriptive fix template**: "Total encoded duration is {actual}s vs expected {expected}s ({diff}s difference). Check segment boundaries: {segment_boundaries}"

### Dimension 8: Boundary Frame Alignment (weight: 10/100)
- **Pass**: Every segment in `encoding-plan.json` has a `boundary_validation` object. For all segments, the face count at first/last 1s matches the expected count for that layout type — OR the boundary was trimmed and the trimmed timestamps are reflected in `start_seconds`/`end_seconds` — OR `no_data_at_boundary: true` is recorded (no face data available, wider crop bias applied).
- **Rework**: `boundary_validation` is present but one or more segments have a face count mismatch at a boundary without a corresponding trim. The agent detected the issue but didn't fix it.
- **Rework**: `boundary_validation` is missing from any segment. The agent skipped the Boundary Frame Guard check entirely.
- **Fail**: Multiple segments show face count mismatches at boundaries with no trimming AND the resulting video would show wrong-crop artifacts for > 1s.
- **Prescriptive fix template**: "Segment {n} has {actual} face(s) at its {start|end} boundary but layout '{layout}' expects {expected}. Trim {start|end}_seconds by 1.0s (from {original} to {adjusted}). Add boundary_validation to encoding-plan.json. See crop-playbook.md § Boundary Frame Guard."

## Scoring Rubric

- 90-100: Excellent — all segments encoded correctly, faces validated, quality within limits, proper dimensions and codec
- 70-89: Good — all segments exist, face validation present, minor quality or codec issues
- 50-69: Acceptable — most segments correct, face validation incomplete or quality borderline
- 30-49: Poor — rework required, face validation missing, encoding failures, or quality unacceptable
- 0-29: Fail — no valid encoded segments, or faces cut off in crops

## Output Schema Requirements

Output JSON (`encoding-plan.json`) must contain:
- `commands`: array of objects with:
  - `input`, `crop_filter`, `output`, `start_seconds`, `end_seconds`
  - `validation`: object with `face_in_crop` (bool), `face_source` (string), `active_speaker` (string)
  - `quality`: object with `upscale_factor` (float), `quality` (string), `recommendation` (string)
  - `boundary_validation`: object with `start_face_count` (int), `end_face_count` (int), `expected_face_count` (int), `start_trimmed` (bool), `end_trimmed` (bool), and optionally `original_start`/`original_end` (float), `adjusted_start`/`adjusted_end` (float), `no_data_at_boundary` (bool)
- `segment_paths`: array of output file paths (all must exist after execution)
- `total_duration_seconds`: float (sum of all segment durations)
