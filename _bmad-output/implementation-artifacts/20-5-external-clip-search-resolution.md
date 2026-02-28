# Story 20-5: External Clip Search & Resolution

## Status: ready-for-dev

## Context

After the Content Creator agent (Stage 4) generates `external_clip_suggestions[]`, a resolver service needs to search YouTube for matching clips, download them, and prepare them for assembly. This runs as a background task in parallel with Veo3 generation, so it doesn't block the pipeline.

## Story

As a pipeline developer,
I want a service that resolves Content Creator clip suggestions into downloadable URLs by searching YouTube,
so that agent-suggested documentary clips are automatically sourced without user intervention.

## Acceptance Criteria

1. Given `application/external_clip_resolver.py`, when created, then it has an `ExternalClipResolver` class

2. Given `resolve(suggestion)`, when called, then it uses `yt-dlp --flat-playlist "ytsearch1:{query}"` to find a YouTube Short matching the search query

3. Given a search result, when filtering, then it prefers vertical format (Shorts) under 60s duration

4. Given the pipeline runner, when the Content stage completes, then the resolver is launched as a fire-and-forget `asyncio.Task`

5. Given the background task, when stored, then it uses `PipelineRunner._background_tasks` dict for lifecycle management

6. Given the resolver, when downloading clips, then it uses `ExternalClipDownloader` (Story 20-1)

7. Given the resolver, when running, then it is rate-limited: max 3 searches per run, 2s delay between searches

8. Given a search failure, when it occurs, then external clips are simply not included (graceful fallback)

9. Given an unhandled exception in the task, when caught, then it is logged and the result is empty (never crashes the pipeline)

## Tasks

- [ ] Task 1: Create `application/external_clip_resolver.py` with `ExternalClipResolver` class
- [ ] Task 2: Implement `_search_youtube(query: str) -> str | None` using yt-dlp ytsearch1
- [ ] Task 3: Implement `resolve_all(suggestions: list[dict], dest_dir: Path) -> list[dict]` with rate limiting
- [ ] Task 4: Wire into `pipeline_runner.py`: launch as background task after CONTENT stage
- [ ] Task 5: Add task to `_background_tasks` dict, handle cancel on abort, await before assembly
- [ ] Task 6: Write resolved clips manifest to `external-clips.json` in workspace
- [ ] Task 7: Unit tests for search, resolve, rate limiting, error handling, background task lifecycle
- [ ] Task 8: Run full test suite, ruff, mypy — all pass

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/application/external_clip_resolver.py` | New file — resolver class | Application layer |
| `src/pipeline/application/pipeline_runner.py` | Launch background task, lifecycle management | Application layer |
| `tests/unit/application/test_external_clip_resolver.py` | New file — unit tests | Tests |

## Dev Notes

### Architecture

This is an **application layer** service. It can import from domain and use ports, but should not import infrastructure directly. The `ExternalClipDownloader` is accessed via the `ExternalClipDownloaderPort` protocol from `domain/ports.py:150`.

### yt-dlp search command

```python
proc = await asyncio.create_subprocess_exec(
    "yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch1:{query}",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

Parse JSON output for `url`, `duration`, `width`, `height`. Filter: `duration <= 60`, prefer vertical (`height > width`).

### Pipeline runner integration

`pipeline_runner.py` already has a `_background_tasks` pattern for Veo3 at lines ~370-400. Follow the same pattern:
1. After CONTENT stage completes, read `publishing-assets.json` for suggestions
2. Launch `asyncio.create_task(self._resolve_external_clips(...))`
3. Store in `self._background_tasks["external_clips"]`
4. Before ASSEMBLY stage, `await self._background_tasks.get("external_clips")`
5. On pipeline abort, cancel the task

### Rate limiting

Use `asyncio.sleep(2.0)` between searches. Max 3 searches enforced by slicing suggestions list.

### Error handling pattern

```python
async def _resolve_external_clips_safe(self, ...) -> None:
    try:
        await self._resolve_external_clips(...)
    except Exception:
        logger.exception("External clip resolution failed — continuing without external clips")
```

### ExternalClipDownloader port

`domain/ports.py:150` — `ExternalClipDownloaderPort` with `download(url, dest_dir) -> Path | None`.

### Line length

120 chars max.

## Definition of Done

- `ExternalClipResolver` class in application layer
- yt-dlp search + download pipeline working
- Background task lifecycle in pipeline_runner
- Rate limiting (max 3, 2s delay)
- Graceful fallback on any failure
- All tests pass, ruff clean, mypy clean
- Min 80% coverage on new code
