# Story 20-1: External Clip Download & Preparation

## Status: review

## Description
Add a new port and adapter for downloading external video clips (e.g., from YouTube, Vimeo) via yt-dlp, stripping audio, and upscaling to 1080x1920 for use as overlay material in reels.

## Tasks
- [x] Task 1: Define ExternalClipDownloaderPort in domain/ports.py
- [x] Task 2: Create ExternalClipDownloader adapter (infrastructure/adapters/external_clip_downloader.py)
- [x] Task 3: Create FakeExternalClipDownloader test double
- [x] Task 4: Unit tests for ExternalClipDownloader (13 tests)
- [x] Task 5: Run full test suite + linting + mypy — all green

## Dev Agent Record

### Files Changed
- `src/pipeline/domain/ports.py` — Added `ExternalClipDownloaderPort` protocol
- `src/pipeline/infrastructure/adapters/external_clip_downloader.py` — New adapter: yt-dlp download, audio strip, upscale, validation
- `tests/unit/infrastructure/test_external_clip_downloader.py` — 13 unit tests + FakeExternalClipDownloader

### Test Results
- 1350 passed, 0 failed
- Coverage: 91.25% (above 80% threshold)
- Ruff: All checks passed
- Mypy: Success, no issues found in 64 source files

### Implementation Notes
- Port follows existing pattern (runtime_checkable Protocol, single async method)
- Adapter uses asyncio.create_subprocess_exec for yt-dlp, ffprobe, and ffmpeg
- All failures are non-fatal: log warning, clean up intermediates, return None
- Pipeline: download -> strip audio (if present) -> upscale (if not 1080x1920) -> validate (duration > 0)
- TYPE_CHECKING guard at bottom confirms protocol conformance
- FakeExternalClipDownloader tracks downloaded URLs, supports fail mode
