# QA Gate: Research

## Evaluation Dimensions

### Dimension 1: Metadata Completeness (weight: 30/100)
- **Pass**: All VideoMetadata fields present (title, duration_seconds, channel, publish_date, description, url)
- **Rework**: Missing 1-2 optional fields (channel, publish_date, description)
- **Fail**: Missing required fields (url, duration_seconds) or metadata is entirely absent
- **Prescriptive fix template**: "Research output is missing metadata fields: {missing_fields}. Re-download metadata and ensure all VideoMetadata fields are populated."

### Dimension 2: Transcript Quality (weight: 30/100)
- **Pass**: Transcript is non-empty, > 100 words, includes timestamp markers
- **Rework**: Transcript exists but is < 100 words, or missing timestamps
- **Fail**: Transcript is empty, "DOWNLOAD_FAILED", or absent from output
- **Prescriptive fix template**: "Re-download subtitles and parse into transcript_text. Current transcript has {word_count} words (minimum: 100). Try auto-generated captions if manual subtitles unavailable."

### Dimension 3: Theme Identification (weight: 20/100)
- **Pass**: 3-7 key themes identified, relevant to episode content
- **Rework**: Fewer than 3 themes or themes are too generic ("conversation", "discussion")
- **Fail**: No themes identified
- **Prescriptive fix template**: "Identify at least 3 specific key themes from the transcript. Current themes ({current_themes}) are too generic. Look for specific topics discussed."

### Dimension 4: Summary Coherence (weight: 20/100)
- **Pass**: Episode summary is 2-3 sentences, coherent, captures main discussion
- **Rework**: Summary exists but is too long (> 5 sentences) or too vague
- **Fail**: No summary or summary is unrelated to transcript content
- **Prescriptive fix template**: "Revise episode_summary to 2-3 concise sentences capturing the main discussion. Current summary is {issue}."

## Scoring Rubric

- 90-100: Excellent — complete metadata, rich transcript, specific themes, clear summary
- 70-89: Good — all required data present, minor quality issues
- 50-69: Acceptable — core data present but gaps in themes or summary
- 30-49: Poor — rework required, missing critical data
- 0-29: Fail — transcript missing or metadata fundamentally broken

## Output Schema Requirements

Output JSON must contain:
- `video_metadata`: object with fields matching VideoMetadata dataclass
- `transcript_text`: non-empty string (> 100 words)
- `episode_summary`: string (2-3 sentences)
- `key_themes`: array of 3-7 strings
- `speakers_identified`: array of strings
