# QA Gate: Assembly

## Evaluation Dimensions

### Dimension 1: Final Video Existence (weight: 25/100)
- **Pass**: Final video file exists, is non-empty, and is a valid MP4 container
- **Rework**: File exists but is suspiciously small (< 1MB for a 30+ second video)
- **Fail**: File does not exist or is corrupt (not a valid MP4)
- **Prescriptive fix template**: "Final video file not found at {path}. Check that concatenation completed successfully and output path matches assembly plan."

### Dimension 2: Dimensions Compliance (weight: 25/100)
- **Pass**: Final video is exactly 1080x1920
- **Rework**: Dimensions are close but not exact (within 4px)
- **Fail**: Dimensions are wrong (not 1080x1920)
- **Prescriptive fix template**: "Final video is {actual_w}x{actual_h} instead of 1080x1920. Check that all input segments have matching dimensions before concatenation."

### Dimension 3: Duration Accuracy (weight: 25/100)
- **Pass**: Duration is within 5% of expected (from moment-selection.json)
- **Rework**: Duration is within 5-10% of expected
- **Fail**: Duration mismatch > 10%
- **Prescriptive fix template**: "Final duration {actual}s vs expected {expected}s (difference: {diff}%). Check concatenation order — segment {n} may be missing or duplicated."

### Dimension 4: Audio Sync (weight: 25/100)
- **Pass**: Audio is present and synchronized with video
- **Rework**: Audio present but minor desync (< 0.5s drift)
- **Fail**: No audio, or audio is severely desynced (> 1s drift)
- **Prescriptive fix template**: "Audio desync detected ({drift}s drift). Re-concatenate with matching audio parameters across all segments. Ensure all segments have same audio sample rate (44100 Hz)."

## Scoring Rubric

- 90-100: Excellent — perfect dimensions, duration matches, audio synced, valid file
- 70-89: Good — file exists, dimensions correct, minor duration or sync issues
- 50-69: Acceptable — file exists but some quality concerns
- 30-49: Poor — rework required, duration mismatch or quality issues
- 0-29: Fail — no valid output or fundamentally broken

## Output Schema Requirements

Output JSON (`assembly-report.json`) must contain:
- `concatenation_order`: array of segment paths in order
- `transitions`: array of transition specs (type, at_seconds)
- `final_output_path`: string path to final video
- `quality_checks`: object with dimensions, duration_seconds, file_size_mb, codec, audio_codec, all_segments_valid, duration_within_tolerance
