# Story 23.1: ODMantic MongoDB Setup & Document Models

Status: ready-for-dev

## Story

As a Developer,
I want to create the MongoDB connection and ODMantic document models,
So that I can persist pipeline events and state projections to a NoSQL database.

## Acceptance Criteria

1. **Given** the configured infrastructure layer, **When** implementing the database models, **Then** `PipelineEventDocument` must be created as an ODMantic `Model` to store immutable state change events, **And** `RunStateDocument` must be created to hold the current projected state of a run.

2. **Given** a MongoDB connection string in `.env`, **When** the application starts, **Then** the `AIOEngine` must connect to MongoDB asynchronously, **And** the connection must be validated with a health check.

3. **Given** the ODMantic models, **When** I inspect their field types, **Then** they must use strict Pydantic types (no `Any`), **And** they must include proper indexes for query performance (`pipeline_run_id`, `created_at`).

4. **Given** the infrastructure layer, **When** I run `mypy --strict`, **Then** zero type errors in `infrastructure/database/` modules.

## Existing Code Audit

- `infrastructure/database/models/run_document.py` — EXISTS with `PipelineEventDocument` (fields: `run_id`, `event_type`, `timestamp`, `stage`, `payload: dict`) and `RunStateDocument` (fields: `run_id`, `youtube_url`, `current_stage`, `status`, `stages_completed`, `created_at`, `updated_at`, `last_event_id`). **BUT** `odmantic` is NOT in pyproject.toml — this code cannot run.
- `infrastructure/database/repositories/mongo_state_store.py` — EXISTS with `MongoStateStore` class implementing `StateStorePort`. **BUT** `motor` is NOT in pyproject.toml.
- No `infrastructure/database/mappers/` directory exists.
- No MongoDB connection manager exists (MongoStateStore creates its own client inline).
- No MongoDB settings in `app/settings.py`.

## Tasks / Subtasks

- [x] **Task 1: MongoDB infrastructure package exists** (AC: #1) [EXISTING]
  - [x] `src/pipeline/infrastructure/database/` exists
  - [x] `src/pipeline/infrastructure/database/models/` exists
  - [ ] Create `src/pipeline/infrastructure/database/mappers/` (NEW — needed for clean separation)

- [ ] **Task 2: Refactor existing PipelineEventDocument** (AC: #1, #3)
  - [ ] **[MODIFY]** Existing model in `run_document.py` has: `run_id`, `event_type`, `timestamp`, `stage`, `payload: dict`
  - [ ] Add `event_id: str` (indexed, unique)
  - [ ] Rename `run_id` → `pipeline_run_id`, `stage` → `stage_name`, `payload` → `payload_data`
  - [ ] **[FIX]** `payload: dict` is untyped — change to `payload_data: dict[str, object]`
  - [ ] Add compound index on `(pipeline_run_id, created_at)`
  - [ ] Split into own file: `infrastructure/database/models/pipeline_event_document.py`

- [ ] **Task 3: Refactor existing RunStateDocument** (AC: #1, #3)
  - [ ] **[MODIFY]** Existing model has: `run_id`, `youtube_url`, `current_stage`, `status`, `stages_completed`, `created_at`, `updated_at`, `last_event_id`
  - [ ] Add missing fields: `trigger_source`, `current_attempt_count`, `qa_evaluation_status`, `escalation_status`
  - [ ] Rename: `run_id` → `pipeline_run_id`, `status` → `execution_status`
  - [ ] Split into own file: `infrastructure/database/models/run_state_document.py`
  - [ ] Delete old `run_document.py` after split

- [ ] **Task 4: Create MongoDB connection manager** (AC: #2)
  - [ ] Create `src/pipeline/infrastructure/database/mongodb_connection_manager.py`
  - [ ] `MongoDbConnectionManager` class with:
    - `async connect(connection_string: str, database_name: str) -> AIOEngine`
    - `async disconnect() -> None`
    - `async health_check() -> bool`
  - [ ] Connection string loaded from `MongoDbSettings(BaseSettings)` in `app/settings.py`
  - [ ] Pool configuration: `maxPoolSize=10`, `serverSelectionTimeoutMS=5000`

- [ ] **Task 5: Create domain-to-document mapper** (AC: #1)
  - [ ] Create `src/pipeline/infrastructure/database/mappers/pipeline_event_mapper.py`
  - [ ] `map_domain_event_to_document(event: PipelineStateEvent) -> PipelineEventDocument`
  - [ ] `map_document_to_domain_event(document: PipelineEventDocument) -> PipelineStateEvent`
  - [ ] Create `src/pipeline/infrastructure/database/mappers/run_state_mapper.py`
  - [ ] `map_projection_to_document(projection: RunStateProjection) -> RunStateDocument`
  - [ ] `map_document_to_projection(document: RunStateDocument) -> RunStateProjection`
  - [ ] All mappers are pure functions (no side effects)

- [ ] **Task 6: Add MongoDB settings to application config** (AC: #2)
  - [ ] Add `MongoDbSettings` to `app/settings.py`:
    - `mongodb_connection_string: str` (from `MONGODB_URI` env var)
    - `mongodb_database_name: str = "telegram_reels_pipeline"`
  - [ ] Update `.env.example` with `MONGODB_URI=mongodb://localhost:27017`

- [ ] **Task 7: Write integration tests** (AC: #1, #2, #3)
  - [ ] `tests/integration/test_mongodb_connection_manager.py`: connect, health check, disconnect
  - [ ] `tests/integration/test_pipeline_event_document.py`: CRUD operations via AIOEngine
  - [ ] `tests/integration/test_run_state_document.py`: CRUD operations, index verification
  - [ ] Use testcontainers or in-memory MongoDB for test isolation

- [ ] **Task 8: Write mapper unit tests** (AC: #1)
  - [ ] `tests/unit/infrastructure/test_pipeline_event_mapper.py`: round-trip conversion
  - [ ] `tests/unit/infrastructure/test_run_state_mapper.py`: round-trip conversion
  - [ ] Verify deep immutability of domain objects after mapping

## Dev Notes

### ODMantic Choice Rationale

ODMantic was selected because (from technical research):
- Built on Pydantic v2.5+ — seamless DTO bridge between Presentation and Infrastructure
- Supports both sync and async (AIOEngine)
- Integrates natively with FastAPI/ASGI
- Cleanest mapping between Presentation DTOs and MongoDB documents

### Mapper Pattern

Mappers live in `infrastructure/database/mappers/` and are the ONLY code that knows both the domain model structure and the ODMantic document structure. This prevents domain contamination:

```
Domain Entity ←→ Mapper ←→ ODMantic Document ←→ MongoDB
```

The Application layer never sees ODMantic models. The Presentation layer never sees ODMantic models. Only the Infrastructure adapter uses the mapper internally.

### Index Strategy

Events are the append-only source of truth. Key query patterns:
- `get_events_for_run(pipeline_run_id)` → compound index `(pipeline_run_id, created_at)`
- `get_latest_projection(pipeline_run_id)` → unique index on `pipeline_run_id`
- `list_pending_runs()` → index on `execution_status` + `created_at`

### MongoDB on Raspberry Pi

MongoDB Community Server runs on ARM64. Resource considerations:
- Use `WiredTiger` storage engine with `cacheSizeGB: 0.5` to limit RAM usage
- Journal writes enabled for crash safety (aligns with NFR-R1)

### References

- [Source: prd.md#State Management & Event Sourcing] — FR6, FR7, FR8
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.1] — ODMantic recommendation
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.3] — Infrastructure Adapter snippet
- [Source: epics.md#Story 2.1] — ODMantic MongoDB Setup
- [Source: CLAUDE.md#Event Sourced State (MongoDB)] — ODMantic + MongoDB requirement
