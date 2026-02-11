# Story 7.2: Research Agent Definition & Metadata Extraction

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Research Agent definition and metadata extraction knowledge file written,
So that the Research stage can download episode metadata, subtitles, and build episode context for moment selection.

## Acceptance Criteria

1. **Given** `agents/research/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the RESEARCH stage,
   **Then** it contains instructions for Claude to: download video metadata, download/parse subtitles, build episode summary, identify key themes and speakers.

2. **Given** the Research Agent executes with a YouTube URL,
   **When** it uses VideoDownloadPort and its own analysis,
   **Then** it outputs structured JSON with: `video_metadata`, `transcript_text`, `episode_summary`, `key_themes`, `speakers_identified`.

3. **Given** `agents/research/metadata-extraction.md` exists,
   **When** the Research Agent references it,
   **Then** it contains rules for extracting structured metadata from YouTube page data, handling missing fields, and normalizing formats.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/research/agent.md` (AC: #1, #2)
  - [ ] Agent persona: "Research" — the episode analyst
  - [ ] Role: Download and analyze episode content, build context for downstream stages
  - [ ] Input contract: YouTube URL from Router output, workspace path
  - [ ] Output contract: JSON with `video_metadata` (VideoMetadata fields), `transcript_text` (full text), `episode_summary` (2-3 sentences), `key_themes` (array of strings), `speakers_identified` (array)
  - [ ] Behavioral rules: always download subtitles first, fall back to auto-generated captions, report missing data clearly
  - [ ] Tool usage: instruct Claude to use yt-dlp MCP tools or file operations

- [ ] Task 2: Write `agents/research/metadata-extraction.md` (AC: #3)
  - [ ] Metadata fields: title, duration, channel, publish_date, description, view_count
  - [ ] Normalization: dates to ISO 8601, durations to seconds, channel names trimmed
  - [ ] Missing field handling: use "unknown" for missing optional fields, fail for missing URL
  - [ ] Subtitle format: prefer .vtt, fall back to .srt, parse timestamps

## Dev Notes

### Output JSON Schema

```json
{
  "video_metadata": {
    "title": "Episode Title",
    "duration_seconds": 3600,
    "channel": "Channel Name",
    "publish_date": "2026-01-15",
    "description": "...",
    "url": "https://youtube.com/watch?v=..."
  },
  "transcript_text": "Full transcript text...",
  "episode_summary": "A discussion about...",
  "key_themes": ["AI safety", "alignment", "governance"],
  "speakers_identified": ["Host Name", "Guest Name"]
}
```

### Integration Points

- **Input**: URL and workspace from Router stage, via `AgentRequest.prior_artifacts`
- **Output**: Written to workspace as `research-output.json`, collected by ArtifactCollector
- **Downstream**: Transcript Agent reads the transcript and metadata to select moments
- **Tools**: VideoDownloadPort (yt-dlp) provides download capabilities

### PRD Functional Requirements

- FR5: Extract video metadata
- FR6: Download and parse subtitles/transcripts

### File Locations

```
telegram-reels-pipeline/agents/research/agent.md                # Main agent definition
telegram-reels-pipeline/agents/research/metadata-extraction.md   # Metadata rules
```

### References

- [Source: prd.md#FR5-FR6] — Metadata and transcript requirements
- [Source: domain/models.py#VideoMetadata] — VideoMetadata frozen dataclass
- [Source: infrastructure/adapters/ytdlp_adapter.py] — YtDlpAdapter implementation
- [Source: pipeline_runner.py#_STAGE_DISPATCH] — Research stage mapping

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
