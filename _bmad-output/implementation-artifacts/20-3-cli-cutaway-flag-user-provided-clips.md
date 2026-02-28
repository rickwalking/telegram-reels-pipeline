# Story 20-3: CLI --cutaway Flag for User-Provided Clips

## Status: done

## Context

Users want to manually specify external video URLs to insert as documentary cutaways at specific narrative moments. The `ExternalClipDownloader` (20-1) can download clips and the `CutawayManifest` (20-2) can merge them with Veo3 clips. This story adds the CLI flag and download orchestration.

## Story

As a pipeline user,
I want to provide external video URLs via `--cutaway` CLI flag with target timestamps,
so that I can manually specify documentary footage to insert at specific narrative moments.

## Acceptance Criteria

1. Given the CLI, when `--cutaway URL@TIMESTAMP` is used, then the URL and insertion timestamp are parsed correctly by splitting on the **last** `@` character

2. Given `--cutaway` used multiple times, when the pipeline starts, then each clip is downloaded via `ExternalClipDownloader` before stage 1

3. Given a downloaded clip, when its duration is detected, then ffprobe auto-detects the duration from the file

4. Given downloaded clips, when saved, then they go to `external_clips/cutaway-{n}.mp4` in the workspace

5. Given successful downloads, when manifested, then `external-clips.json` is written with `[{url, clip_path, insertion_point_s, duration_s}]`

6. Given a download failure for one URL, when other URLs exist, then the others still proceed (partial success)

7. Given `--cutaway` help text, when displayed, then it documents the `URL@TIMESTAMP` format

## Tasks

- [x] Task 1: Add `--cutaway` argument to argparse (action="append", repeatable)
- [x] Task 2: Add `_parse_cutaway_spec(spec: str) -> tuple[str, float]` to parse `URL@TIMESTAMP` by last `@`
- [x] Task 3: Add `_download_cutaway_clips()` async function that downloads all clips via `ExternalClipDownloader`
- [x] Task 4: Add ffprobe duration detection for downloaded clips
- [x] Task 5: Write `external-clips.json` manifest to workspace
- [x] Task 6: Wire cutaway download into CLI main before stage 1 execution
- [x] Task 7: Unit tests for URL parsing (especially URLs with `@` in path), download orchestration, manifest format
- [x] Task 8: Run full test suite, ruff, mypy — all pass

## Files Affected

| File | Change | Type |
|------|--------|------|
| `scripts/run_cli.py` | Add `--cutaway` flag, parse, download, manifest | CLI |
| `tests/unit/test_cli_cutaway.py` | New file — unit tests | Tests |

## Dev Notes

### CLI arg location

Argparse setup at `scripts/run_cli.py:794-816`. Add after `--verbose`:
```python
parser.add_argument(
    "--cutaway",
    action="append",
    default=None,
    metavar="URL@TIMESTAMP",
    help="External clip URL with insertion timestamp (repeatable)",
)
```

### URL parsing

Split on **last** `@` since URLs can contain `@` (e.g., `https://example.com/@user/video@30`):
```python
def _parse_cutaway_spec(spec: str) -> tuple[str, float]:
    idx = spec.rfind("@")
    if idx <= 0:
        raise ValueError(f"Invalid cutaway spec '{spec}': expected URL@TIMESTAMP")
    url = spec[:idx]
    timestamp = float(spec[idx + 1:])
    return url, timestamp
```

### Download orchestration

`ExternalClipDownloader` is at `infrastructure/adapters/external_clip_downloader.py:19`. Its `download(url, dest_dir)` returns `Path | None`.

For ffprobe duration, reuse the pattern from `reel_assembler.py:466-495` (`validate_duration`) or `_probe_resolution`.

### Manifest format

Write `external-clips.json` as a JSON array:
```json
[
  {"url": "...", "clip_path": "external_clips/cutaway-0.mp4", "insertion_point_s": 30.0, "duration_s": 12.5}
]
```

### Import note

`scripts/run_cli.py` adds `src` to path at line 26. Import `ExternalClipDownloader` after that.

### Line length

120 chars max.

## Definition of Done

- `--cutaway URL@TIMESTAMP` flag works, repeatable
- URL parsed by last `@`, timestamp is float
- Clips downloaded before stage 1, manifest written
- Partial success on download failures
- All tests pass, ruff clean, mypy clean
- Min 80% coverage on new code
