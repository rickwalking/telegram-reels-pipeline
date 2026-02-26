# Story 18-2: Authenticated Video Download

## Context

The Veo3 adapter's `download_clip()` was a stub that returned `dest` without actually downloading anything. The Gemini API returns an operation name from `generate_videos()` that must be polled to obtain the video URI, then downloaded with header-based API key authentication (`x-goog-api-key`).

## Story

As a pipeline developer,
I want `download_clip()` to actually download the generated video via authenticated HTTP using the operation name from submit,
so that Veo3-generated B-roll clips are available on disk for assembly.

## Acceptance Criteria

1. Given `Veo3Job`, when constructed, then it includes an `operation_name: str` field (default `""`)
2. Given `submit_job()`, when the API returns an operation, then the operation's `.name` is captured in the returned `Veo3Job.operation_name`
3. Given `download_clip()`, when called with a completed job, then it polls the operation via `client.operations.get()` to retrieve the video URI
4. Given `download_clip()`, when downloading, then it uses `x-goog-api-key` header authentication (not query parameter)
5. Given `download_clip()`, when writing the file, then it uses atomic writes (tmp + rename)
6. Given `download_clip()`, when called with non-COMPLETED status or empty operation_name, then it raises `Veo3GenerationError`
7. Given `jobs.json` serialization, when writing/reading, then `operation_name` is included and defaults to `""` for old files
8. Given `FakeVeo3Adapter`, when `submit_job()` is called, then it returns `operation_name="operations/fake-op-{variant}"`

## Tasks

- [x] Task 1: Add `operation_name: str = ""` to `Veo3Job` frozen dataclass
- [x] Task 2: Update `VideoGenerationPort.submit_job()` docstring
- [x] Task 3: Capture `operation.name` in `GeminiVeo3Adapter.submit_job()`
- [x] Task 4: Implement `download_clip()` with operation polling + authenticated HTTP download
- [x] Task 5: Update `_write_jobs_json()` to include `operation_name`
- [x] Task 6: Update `_read_jobs_json()` to read `operation_name` (default `""`)
- [x] Task 7: Update `FakeVeo3Adapter` for `operation_name`
- [x] Task 8: Unit tests for `Veo3Job` with `operation_name` field
- [x] Task 9: Unit tests for `download_clip()` success and failure paths
- [x] Task 10: Unit tests for `jobs.json` round-trip with `operation_name`
- [x] Task 11: Run full test suite + linting + mypy

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/models.py` | Add `operation_name` field to `Veo3Job` | modify |
| `src/pipeline/domain/ports.py` | Update `submit_job()` docstring | modify |
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | Capture `operation_name` in `submit_job()`, implement `download_clip()` fully, update `FakeVeo3Adapter` | modify |
| `src/pipeline/application/veo3_orchestrator.py` | Add `operation_name` to `_write_jobs_json()` and `_read_jobs_json()` | modify |
| `tests/unit/infrastructure/test_veo3_download.py` | New test file for download and operation_name | new |
| `tests/unit/infrastructure/test_gemini_veo3_adapter.py` | Update existing test for new download_clip behavior | modify |

## Dev Agent Record

- **Status**: review
- **Started**: 2026-02-26
- **Tests**: 1357 passed, 0 failed (20 new tests added)
- **Coverage**: 91.63% (above 80% threshold)
- **Linting**: ruff, mypy, black all pass
- **Notes**: The existing `test_download_completed_returns_dest` test was updated to `test_download_rejects_empty_operation_name` to reflect the new validation that `operation_name` is required for download.
