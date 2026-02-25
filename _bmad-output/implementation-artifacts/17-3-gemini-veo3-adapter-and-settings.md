# Story 17-3: Gemini Veo3 Adapter & Settings

## Context

The `VideoGenerationPort` protocol (Story 17-2) defines the contract. This story creates the concrete `GeminiVeo3Adapter` in the infrastructure layer that implements it using the Gemini API's Veo3 model. It also centralizes ALL Veo3-related configuration in `app/settings.py` as the single owner of Veo3 env vars — other stories reference these settings but do not define them.

The adapter follows the existing pattern: infrastructure adapters live in `src/pipeline/infrastructure/adapters/`, implement a domain port, and are wired in the composition root.

## Story

As a pipeline developer,
I want a `GeminiVeo3Adapter` that implements `VideoGenerationPort` using the Gemini API, with all Veo3 configuration centralized in PipelineSettings,
so that the pipeline can generate Veo3 video clips through a swappable infrastructure adapter with environment-driven configuration.

## Acceptance Criteria

1. Given the infrastructure layer, when `GeminiVeo3Adapter` is created, then it implements all three `VideoGenerationPort` methods (`submit_job`, `poll_job`, `download_clip`)

2. Given `submit_job()` is called with a `Veo3Prompt`, when the Gemini API is invoked, then it requests 9:16 vertical format, silent audio, and duration from the prompt's `duration_s` field

3. Given `submit_job()` is called, when the idempotent key is sent, then the API call includes it for request deduplication

4. Given `poll_job()` is called with an idempotent key, when the API returns status, then it maps to the appropriate `Veo3JobStatus` enum value

5. Given `download_clip()` is called with a completed job, when the video is fetched, then it saves to the specified `dest` path and returns the path

6. Given any API call fails, when an exception is raised, then it uses proper exception chaining (`raise X from Y`) with a descriptive message

7. Given `app/settings.py`, when Veo3 settings are defined, then ALL four env vars are centralized: `GEMINI_API_KEY: str`, `VEO3_CLIP_COUNT: int = 3`, `VEO3_TIMEOUT_S: int = 300`, `VEO3_CROP_BOTTOM_PX: int = 16`

8. Given a test environment, when `FakeVeo3Adapter` is used, then it returns canned `Veo3Job` responses with configurable delays and failure modes

## Tasks

- [ ] Task 1: Add Veo3 settings to `PipelineSettings` in `app/settings.py` (GEMINI_API_KEY, VEO3_CLIP_COUNT, VEO3_TIMEOUT_S, VEO3_CROP_BOTTOM_PX)
- [ ] Task 2: Update `.env.example` with all Veo3 env vars documented
- [ ] Task 3: Research `google-genai` SDK Veo3 API surface (method signatures, auth flow, response format)
- [ ] Task 4: Create `infrastructure/adapters/gemini_veo3_adapter.py` with `GeminiVeo3Adapter` class
- [ ] Task 5: Implement `submit_job()` — API call with 9:16 format, silent audio, idempotent key
- [ ] Task 6: Implement `poll_job()` — status mapping to `Veo3JobStatus` enum
- [ ] Task 7: Implement `download_clip()` — fetch and save video to dest path
- [ ] Task 8: Create `FakeVeo3Adapter` for testing
- [ ] Task 9: Add `google-genai` to Poetry dependencies
- [ ] Task 10: Unit tests for adapter with fake API responses
- [ ] Task 11: Unit tests for settings validation

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/infrastructure/adapters/gemini_veo3_adapter.py` | New file — `GeminiVeo3Adapter` + `FakeVeo3Adapter` | Infrastructure adapter |
| `src/pipeline/app/settings.py` | Add `GEMINI_API_KEY`, `VEO3_CLIP_COUNT`, `VEO3_TIMEOUT_S`, `VEO3_CROP_BOTTOM_PX` | App config |
| `.env.example` | Document all Veo3 env vars | Config |
| `pyproject.toml` | Add `google-genai` dependency | Build |
| `tests/unit/infrastructure/test_gemini_veo3_adapter.py` | New file — adapter tests with fake API | Tests |
| `tests/fakes/fake_veo3_adapter.py` | New file — `FakeVeo3Adapter` for integration tests | Test fixtures |

## Technical Notes

- Task 3 (SDK research) is a spike — the `google-genai` SDK's Veo3 API may differ from what's documented. Developer should verify method signatures, auth patterns, and response schemas before implementing
- The adapter must NOT import domain ports directly (only implements the protocol structurally)
- `FakeVeo3Adapter` should support: configurable delay (simulating generation time), configurable failure rate, returning pre-built test video files
- Settings follow existing Pydantic BaseSettings pattern with `.env` file loading
- `GEMINI_API_KEY` should be validated as non-empty in settings (required for adapter initialization)

## Definition of Done

- `GeminiVeo3Adapter` implements `VideoGenerationPort` with all 3 methods
- `FakeVeo3Adapter` available for testing
- All 4 Veo3 env vars centralized in `PipelineSettings`
- `.env.example` updated
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
