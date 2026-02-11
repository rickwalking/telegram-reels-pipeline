# Story 2.4: Transcript Agent — Moment Selection

Status: done

## Story

As a user,
I want the pipeline to analyze the full transcript and select the most compelling 60-90 second moment,
so that the Reel captures the best part of the episode.

## Acceptance Criteria

1. Given research artifacts and elicitation context are available, when the Transcript Agent executes, then episode subtitles are downloaded via yt-dlp and the full transcript is analyzed for narrative structure, emotional peaks, and quotable statement density
2. Given the user specified a topic focus, when moment selection runs, then scoring is weighted toward segments matching the specified topic
3. Given the transcript analysis is complete, when the agent selects a segment, then a 60-90 second segment is chosen with precise start/end timestamps and the selection rationale is documented
4. Given the moment selection artifact is produced, when the QA gate evaluates, then the critique validates segment length, timestamp precision, and selection rationale quality

## Tasks / Subtasks

- [x] Task 1: Implement SRT/VTT transcript parser
- [x] Task 2: Implement MomentSelection domain model (frozen dataclass with validation)
- [x] Task 3: Implement moment output parser and validator
- [x] Task 4: Write comprehensive tests (26 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 377 tests passing, 91.93% coverage, all linters clean
- SRT/VTT parser: handles both formats, strips HTML tags, BOM-safe, multiline text
- MomentSelection model: validates 30-120s duration, non-negative start, rationale required, topic_match_score 0-1
- Moment output parser: JSON with code fence stripping, validates required fields
- Segment bounds validator: checks against video duration
- entries_to_plain_text: converts entries to timestamped text for agent consumption

### File List

- src/pipeline/domain/models.py (MODIFIED — added MomentSelection)
- src/pipeline/infrastructure/adapters/transcript_parser.py (NEW)
- tests/unit/infrastructure/test_transcript_parser.py (NEW)
