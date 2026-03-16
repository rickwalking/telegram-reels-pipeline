# Story 23.2: StateStorePort Implementation (MongoStateStore)

Status: ready-for-dev

## Story

As a Developer,
I want to implement the `StateStorePort` and `EventStorePort` using the ODMantic models,
So that the core pipeline logic can save and retrieve state without coupling to MongoDB.

## Acceptance Criteria

1. **Given** the `EventStorePort` protocol, **When** implementing `MongoDbEventStoreAdapter`, **Then** it must successfully append a `PipelineStateEvent` as an immutable document, **And** retrieve an ordered event stream for a given `pipeline_run_id`.

2. **Given** the `StateStorePort` protocol, **When** implementing `MongoDbStateStoreAdapter`, **Then** it must persist a `RunStateProjection` and load it by `pipeline_run_id`, **And** list all runs filtered by `execution_status`.

3. **Given** both adapters, **When** I run contract tests, **Then** they must conform to their respective port protocols, **And** the domain layer must have zero knowledge of MongoDB or ODMantic.

4. **Given** a `PipelineStateEvent` is appended, **When** I subsequently query the event stream, **Then** the event must appear in the correct chronological position, **And** the `RunStateDocument` projection must be updated atomically.

## Existing Code Audit

- `infrastructure/database/repositories/mongo_state_store.py` — EXISTS with `MongoStateStore` implementing `StateStorePort`. Has `save_state()`, `load_state()`, `list_incomplete_runs()`. Creates `AsyncIOMotorClient` + `AIOEngine` inline in constructor. Does inline mapping (no mapper functions). **`motor`/`odmantic` NOT in pyproject.toml — non-functional.**
- No `EventStorePort` adapter exists (only `StateStorePort`).
- No in-memory fakes exist for testing.
- No contract tests exist.
- No `TransactionalStateWriter` or atomic event+projection pattern.

## Tasks / Subtasks

- [ ] **Task 1: Implement MongoDbEventStoreAdapter** (AC: #1, #4) [NEW — no event store exists]
  - [ ] Create `src/pipeline/infrastructure/database/adapters/mongodb_event_store_adapter.py`
  - [ ] Implement `EventStorePort` protocol:
    - `async append_event(event: PipelineStateEvent) -> None` — maps to document, saves via AIOEngine
    - `async get_events_for_run(pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]` — queries by run ID, ordered by `created_at`
    - `async get_event_count_for_run(pipeline_run_id: str) -> int`
  - [ ] Use mapper functions for domain ↔ document conversion
  - [ ] Events are append-only — no update or delete methods

- [ ] **Task 2: Refactor existing MongoStateStore into MongoDbStateStoreAdapter** (AC: #2, #4)
  - [ ] **[REWRITE]** Existing `mongo_state_store.py` does inline mapping and creates its own client — refactor to accept `AIOEngine` via injection and use mapper functions
  - [ ] Move to `src/pipeline/infrastructure/database/adapters/mongodb_state_store_adapter.py` (new path)
  - [ ] Implement updated `StateStorePort` protocol:
    - `async save_state_projection(projection: RunStateProjection) -> None` — upsert by `pipeline_run_id`
    - `async load_state_projection(pipeline_run_id: str) -> RunStateProjection | None`
    - `async list_runs_by_status(execution_status: str) -> tuple[RunStateProjection, ...]`
    - `async list_all_run_projections() -> tuple[RunStateProjection, ...]`
  - [ ] Upsert pattern: if document exists for `pipeline_run_id`, update it; otherwise create
  - [ ] Use mapper functions for domain ↔ document conversion

- [ ] **Task 3: Create atomic event-and-projection write** (AC: #4)
  - [ ] Create `src/pipeline/infrastructure/database/adapters/transactional_state_writer.py`
  - [ ] `TransactionalStateWriter` class that:
    - Appends event to `PipelineEventDocument` collection
    - Updates `RunStateDocument` projection atomically
    - Uses MongoDB session/transaction if available, otherwise sequential writes with error recovery
  - [ ] This ensures NFR-R1: no ghost states (projection always matches event stream)

- [ ] **Task 4: Write contract tests for EventStorePort** (AC: #3)
  - [ ] `tests/integration/test_mongodb_event_store_adapter.py`
  - [ ] Test: append single event → retrieve it
  - [ ] Test: append multiple events → retrieve in chronological order
  - [ ] Test: query non-existent run → empty tuple
  - [ ] Test: event immutability (no update method exposed)
  - [ ] Verify adapter satisfies `isinstance(adapter, EventStorePort)` via `@runtime_checkable`

- [ ] **Task 5: Write contract tests for StateStorePort** (AC: #3)
  - [ ] `tests/integration/test_mongodb_state_store_adapter.py`
  - [ ] Test: save projection → load by ID → matches
  - [ ] Test: upsert (save twice) → only latest version stored
  - [ ] Test: list by status → correct filtering
  - [ ] Test: load non-existent → returns None
  - [ ] Verify adapter satisfies `isinstance(adapter, StateStorePort)`

- [ ] **Task 6: Create faked in-memory implementations** (AC: #3)
  - [ ] Create `tests/fakes/fake_event_store.py` — in-memory list-based `EventStorePort`
  - [ ] Create `tests/fakes/fake_state_store.py` — in-memory dict-based `StateStorePort`
  - [ ] These are used by application-layer unit tests (no real DB needed)
  - [ ] Verify fakes also pass the same contract tests

## Dev Notes

### Adapter Independence from Domain

The adapters import from `domain/` and `infrastructure/database/` only. They NEVER import from `application/` or `presentation/`. The domain models (`PipelineStateEvent`, `RunStateProjection`) are the contract boundary.

### Transactional Consistency (NFR-R1)

The `TransactionalStateWriter` ensures that when an event is appended, the projection is also updated. If the projection update fails, the event is still persisted (events are the source of truth). On next read, the system can re-project from events to recover consistency.

### ODMantic Engine Injection

Adapters receive `AIOEngine` via constructor injection:

```python
class MongoDbEventStoreAdapter:
    def __init__(self, odmantic_engine: AIOEngine) -> None:
        self._odmantic_engine = odmantic_engine
```

The composition root creates the engine and injects it into all adapters.

### File Size Limit

Per CLAUDE.md, max 450 lines per file. If an adapter grows beyond this, extract mapper logic into separate files (already done via `mappers/` directory).

### References

- [Source: prd.md#Functional Requirements] — FR6 (immutable events), FR7 (state projection)
- [Source: prd.md#Non-Functional Requirements] — NFR-R1 (zero ghost states), NFR-S1 (high-volume writes)
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.3] — MongoDbStateStoreAdapter snippet
- [Source: epics.md#Story 2.2] — StateStorePort Implementation
- [Source: CLAUDE.md#Dependency Injection] — Constructor injection for adapters
