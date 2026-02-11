# Story 2.3: Research Agent — Episode Metadata & Context

Status: done

## Story

As a user,
I want the pipeline to research the full episode context before selecting moments,
so that moment selection is informed by topic, narrative structure, and episode context.

## Acceptance Criteria

1. Given the Router stage completed with elicitation context, when the Research Agent executes, then video metadata is extracted via yt-dlp: title, duration, channel, publish date, description and saved as a structured artifact
2. Given yt-dlp metadata extraction fails, when the retry logic executes, then up to 3 retries with exponential backoff are attempted and failure after retries raises an error handled by the recovery chain
3. Given research artifacts are produced, when the QA gate evaluates, then the critique validates completeness of metadata and context summary

## Tasks / Subtasks

- [x] Task 1: Implement YtDlpAdapter (VideoDownloadPort)
- [x] Task 2: Add retry with exponential backoff (1s, 2s, 4s)
- [x] Task 3: Write comprehensive tests (13 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 351 tests passing, 91.60% coverage, all linters clean
- YtDlpAdapter: implements VideoDownloadPort (download_metadata, download_subtitles, download_video)
- Exponential backoff: 1s, 2s, 4s across 3 retries
- Metadata parsed from yt-dlp --dump-json into VideoMetadata domain model
- Subtitles: tries manual then auto-generated, SRT format
- Protocol compliance: satisfies VideoDownloadPort runtime check

### File List

- src/pipeline/infrastructure/adapters/ytdlp_adapter.py (NEW)
- tests/unit/infrastructure/test_ytdlp_adapter.py (NEW)
