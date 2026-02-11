# Metadata Extraction Rules

## Required Fields

These fields MUST be present in the output. They map to the `VideoMetadata` frozen dataclass:

| Field | Type | Source | Fallback |
|-------|------|--------|----------|
| `title` | string | yt-dlp `title` | Video page title |
| `duration_seconds` | float | yt-dlp `duration` | Must be positive; fail if unavailable |
| `channel` | string | yt-dlp `uploader` / `channel` | "Unknown Channel" |
| `publish_date` | string | yt-dlp `upload_date` | "unknown" |
| `description` | string | yt-dlp `description` | "" (empty string) |
| `url` | string | Original input URL | Must not be empty; fail if unavailable |

## Normalization Rules

### Dates
- Convert yt-dlp `upload_date` format (YYYYMMDD) to ISO 8601 (YYYY-MM-DD)
- Example: `"20260115"` → `"2026-01-15"`

### Duration
- Convert to float seconds
- Must be positive (validated by VideoMetadata.__post_init__)
- Example: `"3600"` → `3600.0`

### Channel Names
- Trim whitespace
- Remove "- Topic" suffix if present (YouTube auto-generated channels)
- Example: `"  Joe Rogan - Topic  "` → `"Joe Rogan"`

### Descriptions
- Truncate to first 2000 characters if longer (preserve sentence boundaries)
- Strip HTML entities

## Missing Field Handling

- **Required fields** (url, duration_seconds): fail the stage if missing
- **Optional string fields** (channel, publish_date, description): use fallback value
- **Never return null** for any VideoMetadata field — use empty string or default

## Subtitle Format Priority

1. **Manual subtitles** (`.en.vtt`, `.en.srt`) — highest quality
2. **Auto-generated captions** (`.en.vtt` with `[auto]` marker) — acceptable
3. **No subtitles available** — set `transcript_text` to `"NO_SUBTITLES_AVAILABLE"` and log warning

## Subtitle Parsing

- Strip VTT/SRT header metadata
- Remove timestamp lines (but note the timestamps for the transcript)
- Remove formatting tags: `<b>`, `<i>`, `<c>`, etc.
- Collapse duplicate lines (VTT often repeats lines across cue boundaries)
- Join into a single continuous text with timestamp markers: `[HH:MM:SS] text...`
