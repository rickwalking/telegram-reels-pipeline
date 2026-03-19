# Story 22.1: Hexagonal Scaffolding — Presentation Layer & Dependency Upgrade

Status: done

## Story

As a Developer,
I want to extend the existing Hexagonal Architecture with a Presentation layer and add FastAPI/MongoDB/FastMCP dependencies,
So that the codebase is ready for the Omni-Channel refactor without breaking the existing pipeline functionality.

## Acceptance Criteria

1. **Given** the existing project structure, **When** I inspect `src/pipeline/`, **Then** a new `presentation/` directory must exist with sub-packages `api/`, `tools/`, and `dtos/`.

2. **Given** the existing `domain/ports.py`, **When** the refactor is complete, **Then** each Port Protocol must live in its own dedicated file under `domain/ports/` (e.g., `state_store_port.py`, `agent_execution_port.py`), **And** the old `ports.py` must be removed, **And** a `domain/ports/__init__.py` must re-export all ports for backward compatibility.

3. **Given** the updated `pyproject.toml`, **When** I run `poetry install`, **Then** FastAPI, uvicorn, odmantic, motor, and mcp dependencies must be installed, **And** `pytest-bdd` must be available in the dev group.

4. **Given** the new layer structure, **When** I run `mypy --strict` and `ruff check`, **Then** zero errors must be reported across all layers including `presentation/`.

## Existing Code Audit

The following stubs already exist but are **non-functional** (dependencies not in pyproject.toml):
- `presentation/api/routers/runs.py` — FastAPI router with POST/GET, imports `fastapi` (not installed), has tight coupling to `MongoStateStore`
- `presentation/dtos/run_dtos.py` — 3 Pydantic DTOs: `CreateRunRequestDTO`, `RunStateResponseDTO`, `SaveStageDTO`
- `presentation/mcp/server.py` — FastMCP stub with 2 mock tools, imports `fastmcp` (not installed)
- `infrastructure/database/models/run_document.py` — ODMantic models, imports `odmantic` (not installed)
- `infrastructure/database/repositories/mongo_state_store.py` — MongoStateStore, imports `motor`/`odmantic` (not installed)
- `domain/ports.py` — SINGLE file with 11 protocols (needs splitting per CLAUDE.md)
- `pytest-bdd` — already in dev dependencies
- `tests/bdd/` — directory does NOT exist

## Tasks / Subtasks

- [x] **Task 1: Presentation Layer directory structure exists** (AC: #1) [EXISTING]
  - [x] `src/pipeline/presentation/api/routers/` exists
  - [x] `src/pipeline/presentation/dtos/` exists
  - [x] **[MODIFY]** Rename `src/pipeline/presentation/mcp/` → `src/pipeline/presentation/tools/` (per CLAUDE.md convention)
  - [x] Ensure all sub-packages have `__init__.py`
  - [x] **[FIX]** `runs.py` has Hexagonal violation: imports `MongoStateStore` directly from infrastructure — must be removed (old runs.py now only imports StateStorePort from domain)

- [x] **Task 2: Split `domain/ports.py` into individual port files** (AC: #2)
  - [x] Create `src/pipeline/domain/ports/` package directory
  - [x] Extract all 11 existing protocols into individual files:
    - `AgentExecutionPort` → `agent_execution_port.py`
    - `ModelDispatchPort` → `model_dispatch_port.py`
    - `MessagingPort` → `messaging_port.py`
    - `QueuePort` → `queue_port.py`
    - `VideoProcessingPort` → `video_processing_port.py`
    - `VideoDownloadPort` → `video_download_port.py`
    - `StateStorePort` → `state_store_port.py`
    - `FileDeliveryPort` → `file_delivery_port.py`
    - `KnowledgeBasePort` → `knowledge_base_port.py`
    - `ResourceMonitorPort` → `resource_monitor_port.py`
    - `VideoGenerationPort` → `video_generation_port.py`
    - `ExternalClipDownloaderPort` → `external_clip_downloader_port.py`
  - [x] Create `domain/ports/__init__.py` that re-exports all ports (backward compat)
  - [x] Remove old `domain/ports.py`
  - [x] Update all imports across `application/` and `infrastructure/` to use new paths

- [x] **Task 3: Add missing dependencies to pyproject.toml** (AC: #3)
  - [x] `poetry add fastapi uvicorn[standard]` (existing stubs import these but they're NOT installed)
  - [x] `poetry add odmantic motor` (existing DB stubs import these but NOT installed)
  - [x] `poetry add "mcp[cli]"` (existing MCP stub imports `fastmcp` but NOT installed)
  - [x] `poetry add sse-starlette` (Server-Sent Events — new)
  - [x] `pytest-bdd` already in dev dependencies [EXISTING]
  - [x] `poetry add --group dev httpx` (async test client for FastAPI)
  - [ ] Verify `poetry install` succeeds and all deps resolve on ARM aarch64
  - [ ] Verify existing stubs actually run after deps are installed

- [x] **Task 4: Add new port protocols for Omni-Channel architecture** (AC: #2)
  - [x] Create `domain/ports/event_store_port.py`: `EventStorePort` protocol with `append_event()`, `get_events_for_run()`, `get_latest_projection()`
  - [x] Create `domain/ports/sse_broadcast_port.py`: `SseBroadcastPort` protocol with `broadcast_event()`, `subscribe_to_run()`
  - [x] Create `domain/ports/file_storage_port.py`: `FileStoragePort` protocol with `save_binary_asset()`, `get_asset_path()`

- [ ] **Task 5: Update Hexagonal layer import rules** (AC: #4)
  - [x] **[FIX]** `presentation/api/routers/runs.py` imports from `infrastructure` — must use DI only (now imports only from domain ports)
  - [ ] **[FIX]** `application/mappers/run_mappers.py` imports from `presentation` — violates layer rules (application cannot import presentation)
  - [x] Verify `presentation/` imports only from `application/` and `domain/`
  - [ ] Run `mypy --strict` — zero errors
  - [ ] Run `ruff check src/ tests/` — zero violations

- [x] **Task 6: Create BDD test infrastructure** (AC: #3, #4)
  - [x] Create `tests/bdd/` directory with `__init__.py`
  - [x] Create `tests/bdd/features/` directory for `.feature` files
  - [x] Create `tests/bdd/step_defs/` directory for step definitions
  - [x] Add sample feature file `tests/bdd/features/trigger_pipeline_run.feature` (placeholder)
  - [ ] Verify `pytest --collect-only` discovers BDD tests

## Dev Notes

### Updated Layer Architecture (5 Layers)

| Layer | Location | Can Import |
|-------|----------|------------|
| Domain | `src/pipeline/domain/` | stdlib only |
| Application | `src/pipeline/application/` | domain only |
| Presentation | `src/pipeline/presentation/` | application, domain |
| Infrastructure | `src/pipeline/infrastructure/` | domain, application, third-party |
| App | `src/pipeline/app/` | all layers |

The Presentation layer is the **incoming boundary** — it receives HTTP requests (FastAPI) and MCP tool calls (FastMCP), validates them via Pydantic DTOs, and delegates to Application Use Cases. It MUST NOT import from Infrastructure directly.

### Single File per Port Convention

Per updated CLAUDE.md, each `Protocol` must live in its own file. The `domain/ports/__init__.py` must re-export all protocols to maintain backward compatibility:

```python
from pipeline.domain.ports.state_store_port import StateStorePort
from pipeline.domain.ports.agent_execution_port import AgentExecutionPort
# ... etc
```

### Backward Compatibility

The existing pipeline must continue to work after this story. All import paths that currently use `from pipeline.domain.ports import X` must still work via the re-exporting `__init__.py`.

### References

- [Source: prd.md#Technical Architecture Considerations] — FastAPI foundation, Event Sourcing, Hexagonal boundaries
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3] — Expected folder structure with presentation layer
- [Source: epics.md#Story 1.1] — Core Hexagonal Scaffolding acceptance criteria
- [Source: CLAUDE.md#Strict Folder Structure] — `presentation/` directory requirement
- [Source: CLAUDE.md#Single File per Port/Interface] — One Protocol per file
