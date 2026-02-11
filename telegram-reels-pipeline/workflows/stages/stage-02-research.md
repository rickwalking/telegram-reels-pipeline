# Stage 2: Research

## Objective

Download video metadata and subtitles from YouTube, analyze the episode content, and build a comprehensive context package for downstream moment selection.

## Inputs

- **router-output.json**: Contains `url` (YouTube URL) and optional `topic_focus`
- **Workspace path**: Directory for writing output artifacts

## Expected Outputs

- **research-output.json**: Structured episode context

```json
{
  "video_metadata": {
    "title": "...", "duration_seconds": 3600, "channel": "...",
    "publish_date": "2026-01-15", "description": "...", "url": "..."
  },
  "transcript_text": "Full transcript with timestamps...",
  "episode_summary": "2-3 sentence summary...",
  "key_themes": ["theme1", "theme2", "theme3"],
  "speakers_identified": ["Host Name", "Guest Name"]
}
```

## Instructions

1. **Download video metadata** using VideoDownloadPort. Extract title, duration, channel, publish date, description.
2. **Download subtitles** — prefer manually-uploaded, fall back to auto-generated captions.
3. **Parse subtitles** into clean transcript text. Strip formatting, preserve timestamps as inline markers.
4. **Analyze the transcript** to identify 3-7 key themes discussed in the episode.
5. **Identify speakers** by name from video metadata, description, or transcript context.
6. **Write episode summary** — 2-3 concise sentences capturing the main discussion.
7. **Output valid JSON** as `research-output.json`.

## Constraints

- Retry downloads up to 3 times with exponential backoff
- Normalize all metadata fields per `metadata-extraction.md`
- Subtitle format preference: VTT > SRT > auto-generated
- Keep episode summary to 2-3 sentences maximum

## Quality Criteria Reference

See: `workflows/qa/gate-criteria/research-criteria.md`

## Escalation Rules

- Video is private, deleted, or age-restricted → fail stage with clear error
- No subtitles available in any format → continue with metadata only, flag in output
- Rate limited by YouTube → wait and retry (up to 3 attempts)

## Prior Artifact Dependencies

- `router-output.json` from Stage 1 (Router) — provides the YouTube URL
