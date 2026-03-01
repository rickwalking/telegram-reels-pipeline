# Story 20-6: Unified Assembly Integration

## Status: ready-for-dev

## Context

Stories 20-1 through 20-5 created the infrastructure: `ExternalClipDownloader` (20-1), `CutawayManifest` domain model with overlap resolution (20-2), CLI `--cutaway` flag (20-3), Content Creator agent suggestions (20-4), and `ExternalClipResolver` background task (20-5). The `ReelAssembler.assemble_with_broll()` already accepts a `CutawayManifest` and produces an assembly report with source tracking.

This final story **wires everything together**: before the assembly stage runs, a manifest builder reads both Veo3 clips and external clips, merges them into a unified `CutawayManifest`, and writes `cutaway-manifest.json` to workspace. The assembly agent prompt is updated to read this manifest for B-roll overlay instructions.

## Story

As a pipeline developer,
I want a pre-assembly manifest builder that merges Veo3 and external clips into a unified `CutawayManifest`,
so that the assembly stage receives a single, overlap-resolved manifest covering all clip sources.

## Acceptance Criteria

1. Given `application/manifest_builder.py`, when created, then it has a `ManifestBuilder` class with `build(workspace, segments, total_duration_s) -> CutawayManifest`

2. Given `veo3/jobs.json` exists, when building the manifest, then Veo3 clips are resolved via `BrollPlacer.resolve_placements()` and converted to `CutawayClip(source=VEO3)`

3. Given `external-clips.json` exists (CLI `--cutaway` format: array), when building, then each entry with `insertion_point_s` is converted to `CutawayClip(source=USER_PROVIDED)`

4. Given `external-clips.json` exists (resolver format: `{"clips": [...]}`), when building, then each entry is converted to `CutawayClip(source=EXTERNAL)` with `insertion_point_s` derived from `narrative_anchor` matching against segments

5. Given both Veo3 and external clips, when merging, then `CutawayManifest.from_broll_and_external()` resolves overlaps by confidence + source priority

6. Given the built manifest, when serialized, then `cutaway-manifest.json` is written atomically to workspace with all clip details including `source`

7. Given `pipeline_runner.py`, when pre-assembly hook runs, then `ManifestBuilder.build()` is called after awaiting external clips and before dispatching the assembly stage

8. Given `scripts/run_cli.py`, when pre-assembly hook runs, then `ManifestBuilder.build()` is called after Veo3 await gate and before assembly stage dispatch

9. Given the assembly stage prompt (`stage-07-assembly.md`), when updated, then it reads `cutaway-manifest.json` for unified B-roll instructions instead of just `veo3/jobs.json`

10. Given no Veo3 clips and no external clips, when building manifest, then an empty manifest is written and assembly proceeds without B-roll

## Tasks

- [ ] Task 1: Create `application/manifest_builder.py` with `ManifestBuilder` class
- [ ] Task 2: Implement `_read_external_clips(workspace) -> tuple[CutawayClip, ...]` supporting both CLI and resolver formats
- [ ] Task 3: Implement `build(workspace, segments, total_duration_s) -> CutawayManifest` using BrollPlacer + external clip reader + factory merge
- [ ] Task 4: Implement `write_manifest(manifest, dropped, workspace)` — atomic JSON write of `cutaway-manifest.json`
- [ ] Task 5: Wire into `pipeline_runner.py` — call after `_await_external_clips()` before assembly dispatch
- [ ] Task 6: Wire into `scripts/run_cli.py` — call after Veo3 await gate before assembly stage
- [ ] Task 7: Update `workflows/stages/stage-07-assembly.md` — read `cutaway-manifest.json` instead of `veo3/jobs.json` directly
- [ ] Task 8: Unit tests for ManifestBuilder: Veo3 only, external only, both, neither, overlap resolution, both formats
- [ ] Task 9: Run full test suite, ruff, mypy — all pass

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/application/manifest_builder.py` | New file — ManifestBuilder class | Application layer |
| `src/pipeline/application/pipeline_runner.py` | Pre-assembly hook calls ManifestBuilder | Application layer |
| `scripts/run_cli.py` | Pre-assembly hook calls ManifestBuilder | CLI |
| `workflows/stages/stage-07-assembly.md` | Read cutaway-manifest.json for unified B-roll | Agent prompt |
| `tests/unit/application/test_manifest_builder.py` | New file — unit tests | Tests |

## Dev Notes

### Architecture

`ManifestBuilder` lives in the **application layer**. It can import:
- `domain.models`: `CutawayClip`, `ClipSource`, `CutawayManifest`, `BrollPlacement`
- `application.broll_placer`: `BrollPlacer` (same layer)

It MUST NOT import infrastructure (no `ExternalClipResolver`, no `ReelAssembler`).

### ManifestBuilder class

```python
class ManifestBuilder:
    """Build unified CutawayManifest from workspace artifacts."""

    def __init__(self, broll_placer: BrollPlacer) -> None:
        self._broll_placer = broll_placer

    async def build(
        self,
        workspace: Path,
        segments: list[dict[str, object]],
        total_duration_s: float,
    ) -> tuple[CutawayManifest, tuple[CutawayClip, ...]]:
        """Returns (manifest, dropped_clips)."""
        veo3 = self._broll_placer.resolve_placements(workspace, segments, total_duration_s)
        external = self._read_external_clips(workspace, segments, total_duration_s)
        manifest, dropped = CutawayManifest.from_broll_and_external(veo3, external)
        return manifest, dropped
```

### External clips JSON formats

**CLI `--cutaway` format** (written by `run_cli.py:_download_cutaway_clips`):
```json
[
  {"url": "...", "clip_path": "external_clips/cutaway-0.mp4", "insertion_point_s": 30.0, "duration_s": 12.5}
]
```
Detection: top-level is a JSON array.
Source: `ClipSource.USER_PROVIDED` (user specified insertion point).

**Resolver format** (written by `ExternalClipResolver.write_manifest`):
```json
{
  "clips": [
    {"search_query": "...", "url": "...", "local_path": "/abs/path.mp4", "duration": 30, "label": "", "timing_hint": ""}
  ]
}
```
Detection: top-level is a JSON object with `"clips"` key.
Source: `ClipSource.EXTERNAL`.
Insertion point: derive from `narrative_anchor` matching against segments (reuse `BrollPlacer._match_anchor` logic or duplicate it).

### Determining insertion_point_s for resolver clips

For resolver-format clips that lack `insertion_point_s`, use anchor matching:
1. Get `narrative_anchor` from the suggestion (stored in `publishing-assets.json` `external_clip_suggestions[].narrative_anchor`)
2. Match against segments via Jaccard keyword similarity (same logic as `BrollPlacer._match_anchor`)
3. Place clip at segment midpoint

If no `narrative_anchor` is available, spread clips evenly across the reel timeline.

### Loading segments for matching

The segments list needed by `build()` comes from `encoding-plan.json`:
```python
data = json.loads((workspace / "encoding-plan.json").read_text())
segments = [{"start_s": c["start_s"], "end_s": c["end_s"], "transcript_text": c.get("transcript_text", "")}
            for c in data.get("commands", [])]
total_duration = data.get("total_duration_seconds", 90.0)
```

### Pipeline runner integration

In `pipeline_runner.py:_dispatch_stage`, after `await self._await_external_clips()`:

```python
if stage == PipelineStage.ASSEMBLY:
    await self._await_external_clips()
    await self._build_cutaway_manifest(workspace)
```

The `_build_cutaway_manifest` method reads `encoding-plan.json` for segments, calls `ManifestBuilder.build()`, and writes the manifest to workspace.

### CLI integration

In `scripts/run_cli.py`, after the Veo3 await gate (line ~730):

```python
if stage == PipelineStage.ASSEMBLY:
    if veo3_task is not None:
        await _run_veo3_await_gate(...)
        veo3_task = None
    # Build unified cutaway manifest
    await _build_cutaway_manifest(workspace)
```

### Assembly stage prompt update

Update `stage-07-assembly.md` step 4.5 to:
```
4.5. **Load cutaway manifest** — if `cutaway-manifest.json` exists, read the unified
clip manifest. Each entry has `source` (veo3/external/user_provided), `clip_path`,
`insertion_point_s`, `duration_s`, `variant`, and `narrative_anchor`. Use these
pre-resolved positions for B-roll overlay. Include all clip details (with source)
in the assembly report `broll_summary.placements[]`. If the manifest is empty or
missing, proceed without B-roll.
```

### cutaway-manifest.json format

```json
{
  "clips": [
    {
      "source": "veo3",
      "variant": "broll",
      "clip_path": "veo3/clip-broll.mp4",
      "insertion_point_s": 15.0,
      "duration_s": 6.0,
      "narrative_anchor": "discussing AI models",
      "match_confidence": 0.85
    },
    {
      "source": "user_provided",
      "variant": "cutaway",
      "clip_path": "external_clips/cutaway-0.mp4",
      "insertion_point_s": 30.0,
      "duration_s": 12.5,
      "narrative_anchor": "",
      "match_confidence": 1.0
    }
  ],
  "dropped": [
    {
      "source": "external",
      "variant": "cutaway",
      "clip_path": "ext-clip.mp4",
      "insertion_point_s": 16.0,
      "duration_s": 8.0,
      "narrative_anchor": "AI models",
      "match_confidence": 0.4,
      "drop_reason": "overlap_with_veo3_clip"
    }
  ]
}
```

### Atomic write pattern

Use the standard project pattern (write-to-tmp + `os.replace`):
```python
fd, tmp = tempfile.mkstemp(dir=str(workspace), suffix=".tmp")
try:
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, str(manifest_path))
except BaseException:
    with contextlib.suppress(OSError):
        os.unlink(tmp)
    raise
```

### Test strategy

Test combinations:
- Veo3 only (no external-clips.json)
- External only (no veo3/jobs.json)
- Both sources present
- Neither source present (empty manifest)
- CLI format external-clips.json (array)
- Resolver format external-clips.json (object with "clips")
- Overlap between Veo3 and external (verify resolution)
- Missing clip files (graceful skip)
- Pipeline runner integration (mock ManifestBuilder)
- CLI integration (mock ManifestBuilder)

### Line length

120 chars max.

## Definition of Done

- `ManifestBuilder` class in application layer
- Reads both Veo3 (via BrollPlacer) and external clips (both JSON formats)
- Merges via `CutawayManifest.from_broll_and_external()` with overlap resolution
- Writes `cutaway-manifest.json` atomically to workspace
- Wired into both pipeline_runner and CLI before assembly stage
- Assembly stage prompt updated to read unified manifest
- All tests pass, ruff clean, mypy clean
- Min 80% coverage on new code
