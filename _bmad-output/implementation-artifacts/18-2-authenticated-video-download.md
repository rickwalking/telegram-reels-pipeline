# Story 18-2: Authenticated Video Download

## Context

The Veo3 adapter's `download_clip()` method (line 83-93) is a stub — it logs a download attempt and returns the destination path without actually downloading. Production testing revealed that `video.save()` from the google-genai SDK fails with "Saving remote videos is not supported." The working approach discovered during the first production run is:

1. Use `types.GenerateVideosOperation(name=op_name)` to poll completed operations
2. Extract `video.uri` from `op.result.generated_videos[0].video`
3. Download via authenticated HTTP with API key

The current `Veo3Job` domain model has no `operation_name` field, and the `VideoGenerationPort` protocol doesn't return operation names from `submit_job()`.

**Security note (Gemini review):** Using `?key=` query parameter in download URLs leaks credentials in logs/referer headers. Use SDK httpx client with API key in headers instead.

## Story

As a pipeline developer,
I want completed Veo3 clips to be downloaded via the Gemini Files API with proper authentication,
so that the await gate can retrieve generated videos instead of failing with "Saving remote videos is not supported".

## Acceptance Criteria

1. Given a completed Veo3 job, when `download_clip()` is called, then the video is downloaded from the Gemini Files API URI to `veo3/{variant}.mp4`

2. Given the download mechanism, when authenticating, then the API key is passed via HTTP header (not `?key=` query parameter)

3. Given the `Veo3Job` domain model, when extended, then it includes `operation_name: str` for tracking the server-side operation reference

4. Given `submit_job()`, when it returns, then the `Veo3Job` includes the `operation_name` from `operation.name`

5. Given `download_clip()`, when polling the operation, then it uses `types.GenerateVideosOperation(name=op_name)` with `client.operations.get()`

6. Given `download_clip()`, when extracting the video URI, then it reads `op.result.generated_videos[0].video.uri`

7. Given a download failure, when it occurs, then the job is marked as `failed` with `error_message="download_failed"` and the pipeline continues

8. Given `jobs.json`, when written, then it includes `operation_name` for each job to support resume/re-download

## Tasks

- [ ] Task 1: Add `operation_name: str = ""` field to `Veo3Job` in `domain/models.py`
- [ ] Task 2: Update `VideoGenerationPort.submit_job()` return type documentation — `Veo3Job` now includes `operation_name`
- [ ] Task 3: Update `GeminiVeo3Adapter.submit_job()` to capture `operation.name` and return it in the `Veo3Job`
- [ ] Task 4: Implement `GeminiVeo3Adapter.download_clip()` fully
  - [ ] Subtask 4a: Poll operation via `types.GenerateVideosOperation(name=op_name)` + `client.operations.get()`
  - [ ] Subtask 4b: Extract `video.uri` from completed operation result
  - [ ] Subtask 4c: Download via `urllib.request.Request` with `x-goog-api-key` header (not query param)
  - [ ] Subtask 4d: Write to destination path atomically (tmp + rename)
  - [ ] Subtask 4e: Return `Path` on success, raise on failure with descriptive error
- [ ] Task 5: Update `Veo3Orchestrator._write_jobs_json()` to serialize `operation_name`
- [ ] Task 6: Update `Veo3Orchestrator._read_jobs_json()` to deserialize `operation_name`
- [ ] Task 7: Update `FakeVeo3Adapter` to return mock `operation_name` and implement fake download
- [ ] Task 8: Unit tests for `Veo3Job` with `operation_name` field
- [ ] Task 9: Unit tests for `download_clip()` with mock HTTP responses (success + failure)
- [ ] Task 10: Unit tests for jobs.json round-trip with `operation_name`
- [ ] Task 11: Run full test suite, linting, mypy

## Dev Notes

### Architecture

- **Layer changes:** Domain (`models.py` — new field), Infrastructure (`gemini_veo3_adapter.py` — download implementation), Application (`veo3_orchestrator.py` — serialization)
- **Port protocol:** `VideoGenerationPort` in `ports.py` lines 116-152 — `download_clip(job, dest) -> Path` signature stays the same, but `Veo3Job` gains `operation_name`
- **Atomic writes:** Use tmp file + `os.rename()` pattern already established in `_write_jobs_json()` (lines 177-204)

### Key Source Locations

| File | Lines | What |
|------|-------|------|
| `src/pipeline/domain/models.py` | 314-332 | `Veo3Job` — add `operation_name` field after `status` |
| `src/pipeline/domain/ports.py` | 116-152 | `VideoGenerationPort` — `submit_job()` and `download_clip()` protocols |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 44-72 | `submit_job()` — capture `operation.name` from result |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 83-93 | `download_clip()` — STUB to replace |
| `src/pipeline/application/veo3_orchestrator.py` | 177-204 | `_write_jobs_json()` — atomic JSON write |
| `src/pipeline/application/veo3_orchestrator.py` | 206-231 | `_read_jobs_json()` — JSON deserialization |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | 96-142 | `FakeVeo3Adapter` — test double |

### API Pattern (from production testing)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
# Submit returns operation with .name
op = client.models.generate_videos(...)
operation_name = op.name  # e.g., "operations/xxx-yyy"

# Poll completed operation
op_ref = types.GenerateVideosOperation(name=operation_name)
result = client.operations.get(operation=op_ref)
video_uri = result.result.generated_videos[0].video.uri

# Download with auth header (NOT ?key= query param)
import urllib.request
req = urllib.request.Request(video_uri, headers={"x-goog-api-key": api_key})
urllib.request.urlretrieve(video_uri, dest)  # Replace with header-based approach
```

### Coding Patterns

- Frozen dataclasses — `operation_name` must have default value (`""`) for backward compatibility
- Exception chaining: `raise Veo3GenerationError("download failed") from e`
- Log at `INFO` for success, `WARNING` for failure

## Definition of Done

- `Veo3Job.operation_name` field persisted in `jobs.json`
- `download_clip()` fully implemented with header-based auth
- `FakeVeo3Adapter` updated for test coverage
- All tests pass, linters clean, mypy clean
- Min 80% coverage on changed code

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List

### Change Log

## Status

ready-for-dev
