# Story 17-2: VideoGenerationPort Protocol

## Context

The pipeline's hexagonal architecture defines port protocols in `domain/ports.py`. There are currently 10 protocols: AgentExecutionPort, ModelDispatchPort, MessagingPort, QueuePort, VideoProcessingPort, VideoDownloadPort, StateStorePort, FileDeliveryPort, KnowledgeBasePort, and ResourceMonitorPort. All follow the same conventions: `@runtime_checkable`, docstrings, async methods, imported via `TYPE_CHECKING` guard in the application layer.

This story adds `VideoGenerationPort` as the 11th port protocol, defining the contract for async video generation services. The application layer will depend on this abstraction; the concrete Gemini Veo3 adapter (Story 17-3) will implement it in the infrastructure layer.

## Story

As a pipeline developer,
I want a `VideoGenerationPort` protocol defining the contract for async video generation services,
so that the domain and application layers depend on an abstraction, not on Gemini-specific implementation details.

## Acceptance Criteria

1. Given `domain/ports.py`, when `VideoGenerationPort` is added, then it is the 11th `@runtime_checkable` Protocol class following existing conventions

2. Given the protocol, when its methods are defined, then it includes:
   - `async submit_job(prompt: Veo3Prompt) -> Veo3Job` — submit a generation request
   - `async poll_job(idempotent_key: str) -> Veo3Job` — check job status
   - `async download_clip(job: Veo3Job, dest: Path) -> Path` — download completed clip to local path

3. Given the protocol, when type-checked, then all method signatures use domain types only (`Veo3Prompt`, `Veo3Job` from `domain/models.py`, `Path` from `pathlib`)

4. Given the application layer, when importing `VideoGenerationPort`, then it uses a `TYPE_CHECKING` guard per project convention

5. Given a class that implements all three methods with matching signatures, when `isinstance()` is called with `VideoGenerationPort`, then it returns `True` (structural subtyping)

## Tasks

- [ ] Task 1: Add `VideoGenerationPort` protocol class to `domain/ports.py` after `ResourceMonitorPort`
- [ ] Task 2: Define `submit_job`, `poll_job`, `download_clip` async method signatures
- [ ] Task 3: Add docstrings to protocol class and each method
- [ ] Task 4: Unit tests for structural subtyping (fake class implements protocol)
- [ ] Task 5: Unit test verifying `runtime_checkable` isinstance check works

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/ports.py` | Add `VideoGenerationPort` protocol (11th port) | Domain port |
| `tests/unit/domain/test_video_generation_port.py` | New file — structural subtyping + isinstance tests | Tests |

## Technical Notes

- Import `Veo3Prompt` and `Veo3Job` from `domain.models` — this is a domain-to-domain import, which is allowed
- Import `Path` from `pathlib` — stdlib, allowed in domain layer
- The `download_clip` method takes a `dest: Path` parameter (where to save) and returns the actual saved `Path` — this follows the same pattern as `VideoDownloadPort.download_video`
- Do not import any third-party types (no `google.genai` types in the port)

## Definition of Done

- `VideoGenerationPort` in `domain/ports.py` with 3 async methods
- Follows all existing port conventions (runtime_checkable, docstrings, async)
- Structural subtyping tests pass
- All tests pass, linters clean, mypy clean
