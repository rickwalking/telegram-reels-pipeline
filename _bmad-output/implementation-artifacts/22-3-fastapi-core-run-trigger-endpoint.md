# Story 22.3: FastAPI Core & Run Trigger Endpoint

Status: ready-for-dev

## Story

As a System Operator,
I want to trigger a new pipeline run via a REST API endpoint,
So that I can programmatically start processing a YouTube URL from any external client (Web UI, Telegram adapter, CI).

## Acceptance Criteria

1. **Given** the FastAPI application is running, **When** a `POST /api/runs` request is made with a valid YouTube URL and optional topic, **Then** the request must be validated using a `CreatePipelineRunRequestDTO`, **And** a new pipeline run must be created with a unique ID and `PipelineStage.ROUTER` state, **And** the response must return a `PipelineRunResponseDTO` containing the newly created run ID within <500ms latency.

2. **Given** a `POST /api/runs` request with an invalid URL, **When** the request is processed, **Then** the API must return HTTP 422 with a structured error body describing the validation failure.

3. **Given** the FastAPI application, **When** I access `/docs`, **Then** comprehensive OpenAPI documentation must be available for all endpoints with proper error code descriptions.

4. **Given** a BDD feature file `trigger_pipeline_run.feature`, **When** I run `pytest tests/bdd/`, **Then** all scenarios must pass including the happy path and validation error scenarios.

## Existing Code Audit

- `presentation/api/routers/runs.py` — stub with POST/GET endpoints, but has **Hexagonal violations**: imports `MongoStateStore` directly, uses mock inline logic to create `RunState`, no real use case
- `presentation/dtos/run_dtos.py` — has `CreateRunRequestDTO` (with `youtube_url`, `topic_focus`, `client_type`, `client_id`), `RunStateResponseDTO`, `SaveStageDTO` (uses `dict` which is effectively `Any`)
- `application/mappers/run_mappers.py` — has `map_runstate_to_response_dto()` but **violates layer rules** (application imports from presentation)
- `app/main.py` — entry point for daemon only (Telegram polling loop), no FastAPI
- `app/bootstrap.py` — composition root wires FileStateStore, CliBackend, etc. — no FastAPI wiring
- `app/settings.py` — Pydantic BaseSettings but no MongoDB or FastAPI settings
- **No FastAPI app factory, no CORS, no middleware, no exception handlers exist**

## Tasks / Subtasks

- [ ] **Task 1: Create FastAPI application factory** (AC: #1, #3)
  - [ ] Create `src/pipeline/presentation/api/application_factory.py`
  - [ ] Define `create_fastapi_application() -> FastAPI` factory function
  - [ ] Configure CORS middleware for React SPA origin
  - [ ] Include `/api` prefix router
  - [ ] Add OpenAPI metadata (title, version, description)
  - [ ] Register exception handlers for domain errors → HTTP responses

- [ ] **Task 2: Refactor existing Pydantic DTOs** (AC: #1, #2)
  - [ ] **[MODIFY]** Existing `CreateRunRequestDTO` in `run_dtos.py` has `client_type`/`client_id` — rename to `trigger_source` per domain model, split into own file
  - [ ] **[MODIFY]** Existing `RunStateResponseDTO` — add `trigger_source`, rename `status` → `execution_status`, split into own file
  - [ ] **[FIX]** Existing `SaveStageDTO` uses `payload: dict` (effectively `Any`) — must use strict types per CLAUDE.md
  - [ ] Create `src/pipeline/presentation/dtos/create_pipeline_run_request_dto.py` (extracted from run_dtos.py):
    - Add custom YouTube URL pattern validator
  - [ ] Create `src/pipeline/presentation/dtos/pipeline_run_response_dto.py` (extracted from run_dtos.py)
  - [ ] Create `src/pipeline/presentation/dtos/error_response_dto.py` (NEW):
    - Fields: `error_code: str`, `error_message: str`, `details: list[dict[str, str]] | None`
  - [ ] Remove old `run_dtos.py` monolith after extraction

- [ ] **Task 3: Create pipeline run trigger use case** (AC: #1)
  - [ ] Create `src/pipeline/application/use_cases/trigger_pipeline_run_use_case.py`
  - [ ] Define `TriggerPipelineRunUseCase` class with injected `EventStorePort` and `StateStorePort`
  - [ ] Method: `async execute(command: CreatePipelineRunCommand) -> RunStateProjection`
  - [ ] Must generate unique `pipeline_run_id`, create initial event, persist to store
  - [ ] Use Result monad pattern for expected failures (return `Result[RunStateProjection, DomainError]`)

- [ ] **Task 4: Rewrite FastAPI router for runs** (AC: #1, #2, #3)
  - [ ] **[REWRITE]** Existing `presentation/api/routers/runs.py` has Hexagonal violations (imports `MongoStateStore` directly, inline mock logic) — must be rewritten
  - [ ] Move to `src/pipeline/presentation/api/pipeline_runs_router.py` (new file, cleaner name)
  - [ ] Define `POST /api/runs` endpoint using proper DI via `Depends()`
  - [ ] Map DTO → Domain command (`CreatePipelineRunRequestDTO` → `CreatePipelineRunCommand`)
  - [ ] Call use case, map result → response DTO
  - [ ] Handle validation errors with structured 422 response
  - [ ] Handle domain errors with appropriate HTTP codes (400, 409, 500)
  - [ ] Add comprehensive OpenAPI docstrings with response examples
  - [ ] Delete old `runs.py` after migration

- [ ] **Task 5: Create exception-to-HTTP mapping decorator** (AC: #2)
  - [ ] Create `src/pipeline/presentation/api/exception_handlers.py`
  - [ ] Map `DomainValidationError` → 400
  - [ ] Map `ConfigurationError` → 500
  - [ ] Map `PipelineError` (generic) → 500
  - [ ] Map Pydantic `ValidationError` → 422
  - [ ] All error responses use `ErrorResponseDTO` format

- [ ] **Task 6: Wire FastAPI into composition root** (AC: #1)
  - [ ] **[MODIFY]** Existing `app/main.py` (143 lines) runs daemon loop only — add FastAPI startup path
  - [ ] **[MODIFY]** Existing `app/bootstrap.py` (198 lines) wires `FileStateStore`, `CliBackend`, etc. — extend with MongoDB and FastAPI dependencies
  - [ ] **[MODIFY]** Existing `app/settings.py` (62 lines) — add `MongoDbSettings` (connection_string, database_name) and `FastApiSettings` (host, port, cors_origins)
  - [ ] Create `src/pipeline/app/api_bootstrap.py` with FastAPI-specific DI wiring
  - [ ] FastAPI `Depends()` resolves ports from composition root
  - [ ] Ensure existing Telegram daemon path is unaffected (two entry points: daemon vs API server)
  - [ ] **[FIX]** `application/mappers/run_mappers.py` imports from `presentation` (layer violation) — move mapper to presentation layer or invert dependency

- [ ] **Task 7: Write BDD feature file and step definitions** (AC: #4)
  - [ ] Create `tests/bdd/features/trigger_pipeline_run.feature`:
    - Scenario: Successfully trigger a new pipeline run
    - Scenario: Reject invalid YouTube URL
    - Scenario: Reject missing required fields
  - [ ] Create `tests/bdd/step_defs/test_trigger_pipeline_run.py` with Given/When/Then steps
  - [ ] Use `httpx.AsyncClient` as test transport for FastAPI
  - [ ] Use faked `EventStorePort` and `StateStorePort` implementations

- [ ] **Task 8: Write unit tests for use case** (AC: #4)
  - [ ] `tests/unit/application/test_trigger_pipeline_run_use_case.py`
  - [ ] Test happy path: command → event created → state projected
  - [ ] Test validation failure: invalid URL → Result error
  - [ ] Use faked ports (no real DB)

## Dev Notes

### Presentation Layer Responsibilities

The Presentation layer (FastAPI router) is responsible for:
1. **Syntactic validation** — Pydantic DTO validates incoming JSON (Gate 1)
2. **DTO → Domain mapping** — Convert validated DTO to domain `CreatePipelineRunCommand`
3. **Use case invocation** — Call application layer
4. **Response mapping** — Convert domain result to response DTO
5. **Error translation** — Map domain exceptions to HTTP status codes

It must NOT contain business logic or interact with infrastructure directly.

### API Design Conventions

- All API endpoints under `/api/` prefix
- Use plural nouns for resources: `/api/runs`, not `/api/run`
- Standard HTTP codes: 201 (created), 400 (bad request), 422 (validation), 500 (internal)
- Every endpoint has OpenAPI documentation with examples
- Error responses always use `ErrorResponseDTO` format

### Dependency Injection Pattern

Use FastAPI's `Depends()` with a composition root:

```python
async def get_trigger_pipeline_run_use_case(
    event_store: EventStorePort = Depends(get_event_store_port),
) -> TriggerPipelineRunUseCase:
    return TriggerPipelineRunUseCase(event_store_port=event_store)
```

The composition root resolves concrete adapters; the router only sees protocols.

### NFR Compliance

- NFR-P1: API latency <500ms — test with `httpx` timing assertions
- NFR-S2: Architecture supports multiple presentation layers — Telegram adapter will use the same use case

### References

- [Source: prd.md#Endpoint Specifications] — `POST /runs` endpoint spec
- [Source: prd.md#Functional Requirements] — FR1 (trigger via URL)
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.2] — FastMCP + FastAPI integration
- [Source: epics.md#Story 1.3] — FastAPI Core & Run Trigger Endpoint
- [Source: CLAUDE.md#Controller Error Handling] — Exception decorator pattern
- [Source: CLAUDE.md#API Documentation] — OpenAPI requirement
