# Story 20-1: External Clip Download & Preparation

## Context

During the first production run, we manually downloaded an external YouTube Short (documentary footage of a baby in an AI-generated scene) using `yt-dlp`, stripped audio, upscaled from 720x1280 to 1080x1920, and overlaid it as a documentary cutaway at 30s in the final reel. This manual workflow needs to be automated as a reusable service that can download external clips from YouTube Shorts, TikTok, and direct URLs.

**Key requirements from production:**
- External clips are VIDEO-ONLY overlays (base reel audio continues)
- Clips must be upscaled to 1080x1920 (hardcoded target, per Gemini review)
- Download failures are non-fatal (clip skipped, pipeline continues)
- Service must be testable via port protocol pattern

## Story

As a pipeline developer,
I want a service that downloads external video clips from YouTube Shorts and prepares them for overlay,
so that external documentary footage can be integrated into the assembly pipeline.

## Acceptance Criteria

1. Given a YouTube Shorts URL, when `download()` is called, then the video is downloaded via `yt-dlp` subprocess

2. Given a downloaded clip, when prepared, then audio is stripped (`-an` flag) — documentary cutaways use base reel audio only

3. Given a clip with non-1080x1920 resolution, when prepared, then it is upscaled to 1080x1920 using `scale=1080:1920:flags=lanczos`

4. Given a clip already at 1080x1920, when prepared, then upscaling is skipped (no-op fast path)

5. Given the prepared clip, when validated, then it exists as a valid video (ffprobe check), duration > 0

6. Given the prepared clip, when stored, then it is written to `external_clips/` subfolder of workspace

7. Given a `yt-dlp` failure (network error, unavailable video), when it occurs, then the method logs a warning and returns `None` — clip is skipped, not pipeline-fatal

8. Given the service, when tested, then `ExternalClipDownloaderPort` protocol in `domain/ports.py` enables fake implementation

## Tasks

- [ ] Task 1: Define `ExternalClipDownloaderPort` protocol in `domain/ports.py`
  - [ ] Subtask 1a: `async def download(self, url: str, dest_dir: Path) -> Path | None`
  - [ ] Subtask 1b: Docstring specifying return `None` on failure (not exception)
- [ ] Task 2: Create `infrastructure/adapters/external_clip_downloader.py` with `ExternalClipDownloader` class
  - [ ] Subtask 2a: `download()` method calls `yt-dlp` subprocess: `yt-dlp -f 'bestvideo[ext=mp4]' --no-audio -o {dest} {url}`
  - [ ] Subtask 2b: Strip audio with FFmpeg if yt-dlp output includes audio: `ffmpeg -i input -an -c:v copy output`
  - [ ] Subtask 2c: Probe resolution via `ffprobe -v error -select_streams v:0 -show_entries stream=width,height`
  - [ ] Subtask 2d: Upscale to 1080x1920 if needed: `ffmpeg -i input -vf 'scale=1080:1920:flags=lanczos' output`
  - [ ] Subtask 2e: Validate output: file exists, ffprobe confirms video stream, duration > 0
  - [ ] Subtask 2f: Return `Path` to prepared clip in `external_clips/` subfolder
  - [ ] Subtask 2g: On any failure: log warning, clean up partial files, return `None`
- [ ] Task 3: Create `FakeExternalClipDownloader` for tests
  - [ ] Subtask 3a: Constructor accepts `fail: bool = False` flag
  - [ ] Subtask 3b: On success: create zero-byte `.mp4` file, return path
  - [ ] Subtask 3c: On failure: return `None`
- [ ] Task 4: Unit tests for `ExternalClipDownloader`
  - [ ] Subtask 4a: Test download command construction (verify yt-dlp args)
  - [ ] Subtask 4b: Test audio stripping when audio track present
  - [ ] Subtask 4c: Test upscale triggered for non-1080x1920
  - [ ] Subtask 4d: Test no-op when already 1080x1920
  - [ ] Subtask 4e: Test yt-dlp failure returns `None` (not exception)
  - [ ] Subtask 4f: Test partial file cleanup on failure
- [ ] Task 5: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer:** Domain port (`ports.py`) + Infrastructure adapter (`external_clip_downloader.py`)
- **Hexagonal pattern:** Same as `VideoGenerationPort` / `GeminiVeo3Adapter` — protocol in domain, implementation in infrastructure
- **Error handling:** Returns `None` on failure (not exceptions) — caller decides whether to skip or retry
- **Hardcoded target:** 1080x1920 (per Gemini review — don't infer from segments)

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/domain/ports.py` | 116-152 | `VideoGenerationPort` — pattern to follow for new port |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 96-142 | `FakeVeo3Adapter` — pattern for fake implementation |
| `src/pipeline/infrastructure/adapters/reel_assembler.py` | 63-416 | `ReelAssembler` — subprocess call patterns for FFmpeg/ffprobe |

### External Tool Dependencies

| Tool | Usage | Fallback |
|------|-------|----------|
| `yt-dlp` | Download videos from YouTube/TikTok | Return `None` if not installed |
| `ffmpeg` | Strip audio, upscale | Required (already a project dependency) |
| `ffprobe` | Probe resolution and validate | Required (bundled with ffmpeg) |

### Coding Patterns

- `asyncio.create_subprocess_exec` for subprocess calls (non-blocking)
- `logging.getLogger(__name__)` for all logging
- Atomic writes: write to tmp file, rename on success
- Cleanup partial files in `finally` block

## Definition of Done

- `ExternalClipDownloaderPort` protocol defined
- `ExternalClipDownloader` downloads, strips audio, upscales, validates
- `FakeExternalClipDownloader` for tests
- Failure returns `None` (non-fatal)
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log

## Status

ready-for-dev
