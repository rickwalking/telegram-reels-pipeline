# Story 1.2: Pipeline State Machine & File Persistence

Status: done

## Story

As a developer,
I want a working FSM that tracks pipeline state and persists it to disk atomically,
So that the pipeline can track stage progression and survive restarts. (FR35, FR40)

## Acceptance Criteria

1. **Given** the PipelineStateMachine is initialized, **When** a valid transition is requested (e.g., ROUTER → RESEARCH after QA pass), **Then** the state transitions and RunState reflects the new stage.

2. **Given** an invalid transition is requested, **When** the FSM evaluates guards, **Then** the transition is rejected with a descriptive PipelineError.

3. **Given** a state change occurs, **When** the FileStateStore persists RunState, **Then** `run.md` is written atomically (write-to-temp + rename), **And** frontmatter matches the exact schema: run_id, youtube_url, current_stage, current_attempt, qa_status, stages_completed, escalation_state, best_of_three_overrides, created_at, updated_at.

4. **Given** a persisted `run.md` exists, **When** FileStateStore loads it, **Then** RunState is correctly reconstructed from frontmatter.

## Tasks / Subtasks

- [x] **Task 1: Create PipelineStateMachine** (AC: #1, #2)
  - [x] Create `src/pipeline/application/state_machine.py`
  - [x] `apply_transition(state: RunState, event: str) -> RunState` — validates transition, returns new immutable RunState
  - [x] Use `dataclasses.replace()` to create new RunState (frozen dataclasses)
  - [x] On `qa_pass`: stages_completed += current stage, current_stage = next, current_attempt = 1, qa_status = PENDING
  - [x] On `qa_rework`: current_attempt += 1, qa_status = REWORK
  - [x] On `qa_fail`: qa_status = FAILED
  - [x] On `stage_complete`: stages_completed += current stage, current_stage = COMPLETED
  - [x] On `unrecoverable_error`: current_stage = FAILED
  - [x] On `escalation_requested` / `escalation_resolved`: update escalation_state accordingly
  - [x] Always update `updated_at` to current ISO 8601 timestamp
  - [x] Raise `ValidationError` with descriptive message on invalid transition
  - [x] `validate_transition(state: RunState, event: str) -> bool` — read-only check

- [x] **Task 2: Create frontmatter serialization helpers** (AC: #3, #4)
  - [x] Create `src/pipeline/infrastructure/adapters/frontmatter.py`
  - [x] `serialize_run_state(state: RunState) -> str` — converts RunState to YAML frontmatter string with `---` delimiters
  - [x] `deserialize_run_state(content: str) -> RunState` — parses frontmatter from run.md content, reconstructs RunState
  - [x] Handle enum serialization: `PipelineStage.RESEARCH` → `"research"` (use `.value`)
  - [x] Handle enum deserialization: `"research"` → `PipelineStage("research")`
  - [x] Handle `QAStatus`, `EscalationState` the same way
  - [x] Handle `tuple` ↔ `list` conversion (domain uses tuples, YAML produces lists)
  - [x] Handle `RunId` NewType (transparently str)
  - [x] Use `pyyaml` (`yaml.safe_dump` / `yaml.safe_load`) — already in runtime deps

- [x] **Task 3: Create FileStateStore adapter** (AC: #3, #4)
  - [x] Create `src/pipeline/infrastructure/adapters/file_state_store.py`
  - [x] Implements `StateStorePort` protocol (async methods)
  - [x] Constructor takes `base_dir: Path` (path to `workspace/runs/`)
  - [x] `async save_state(state: RunState) -> None` — serialize + atomic write to `{base_dir}/{run_id}/run.md`
  - [x] `async load_state(run_id: RunId) -> RunState | None` — read run.md, deserialize; return None if not found
  - [x] `async list_incomplete_runs() -> list[RunState]` — walk base_dir, load all run.md, filter non-terminal
  - [x] Atomic write pattern: write to `.tmp`, then `rename()` (same filesystem = atomic)
  - [x] Create run directory if it doesn't exist (`mkdir(parents=True, exist_ok=True)`)
  - [x] Use `aiofiles` for async file I/O — already in runtime deps

- [x] **Task 4: Write PipelineStateMachine unit tests**
  - [x] Create `tests/unit/application/test_state_machine.py`
  - [x] Test qa_pass transitions each stage forward correctly
  - [x] Test qa_rework stays on same stage and increments attempt
  - [x] Test qa_fail stays on same stage and sets status FAILED
  - [x] Test stage_complete from DELIVERY → COMPLETED
  - [x] Test unrecoverable_error from any stage → FAILED
  - [x] Test escalation_requested / escalation_resolved update escalation_state
  - [x] Test invalid transition raises ValidationError
  - [x] Test stages_completed accumulates correctly across multiple transitions
  - [x] Test updated_at changes on each transition
  - [x] Use domain fixtures from conftest.py (sample_run_state)

- [x] **Task 5: Write FileStateStore integration tests**
  - [x] Create `tests/integration/test_file_state_store.py`
  - [x] Test save_state creates run.md with correct frontmatter
  - [x] Test load_state reconstructs RunState from persisted file
  - [x] Test round-trip: save → load → assert equal
  - [x] Test load_state returns None for non-existent run
  - [x] Test list_incomplete_runs finds only non-terminal runs
  - [x] Test atomic write: .tmp file is cleaned up after rename
  - [x] Test frontmatter enum serialization (PipelineStage, QAStatus, EscalationState round-trip)
  - [x] Use `tmp_path` pytest fixture for filesystem isolation

- [x] **Task 6: Run full validation suite**
  - [x] `poetry run pytest tests/ -v --tb=short` — all tests pass, 80%+ coverage
  - [x] `poetry run mypy` — zero errors (no path arg, uses pyproject.toml config)
  - [x] `poetry run black --check src/ tests/`
  - [x] `poetry run isort --check-only src/ tests/`
  - [x] `poetry run ruff check src/ tests/`

## Dev Notes

### Architecture Compliance (CRITICAL)

**Application Layer Rules** (`src/pipeline/application/`):
- Imports from `domain/` ONLY — no third-party, no infrastructure
- `state_machine.py` imports: `domain.enums`, `domain.models`, `domain.errors`, `domain.transitions`, `domain.types`
- Uses `dataclasses.replace()` from stdlib to create new frozen RunState instances
- Pure logic, no I/O — all file operations delegated to infrastructure via ports

**Infrastructure Layer Rules** (`src/pipeline/infrastructure/adapters/`):
- Imports from `domain/` and `application/` — plus third-party (pyyaml, aiofiles)
- `file_state_store.py` implements `StateStorePort` protocol from `domain.ports`
- `frontmatter.py` is a helper module — serialization/deserialization utilities

### Existing Domain Types (from Story 1.1)

These are ALREADY implemented and tested — do NOT recreate:

```python
# domain/types.py — NewType aliases
RunId = NewType("RunId", str)

# domain/enums.py — all enums
PipelineStage  # ROUTER, RESEARCH, ..., COMPLETED, FAILED
QADecision     # PASS, REWORK, FAIL
QAStatus       # PENDING, PASSED, REWORK, FAILED  ← Added in review
EscalationState  # NONE, LAYOUT_UNKNOWN, QA_EXHAUSTED, ERROR_ESCALATED

# domain/models.py — frozen dataclasses with __post_init__ validation
RunState(run_id, youtube_url, current_stage, current_attempt=1,
         qa_status=QAStatus.PENDING, stages_completed=(), escalation_state=...,
         best_of_three_overrides=(), created_at="", updated_at="")
# NOTE: stages_completed and best_of_three_overrides are tuple[str, ...] (NOT list)
# NOTE: qa_status is QAStatus enum (NOT str)
# NOTE: RunState has __post_init__ validation: run_id not empty, youtube_url not empty, current_attempt >= 1

# domain/errors.py — exception hierarchy
PipelineError(message: str)  # No 'cause' param — use 'raise X from Y' for chaining
ValidationError(PipelineError)

# domain/transitions.py — pure data
TRANSITIONS: dict[tuple[PipelineStage, str], PipelineStage]
STAGE_ORDER: list[PipelineStage]
TERMINAL_STAGES: frozenset[PipelineStage]
MAX_QA_ATTEMPTS: int = 3
is_valid_transition(current, event) -> bool
get_next_stage(current, event) -> PipelineStage | None
is_terminal(stage) -> bool

# domain/ports.py — StateStorePort protocol
class StateStorePort(Protocol):
    async def save_state(self, state: RunState) -> None: ...
    async def load_state(self, run_id: RunId) -> RunState | None: ...
    async def list_incomplete_runs(self) -> list[RunState]: ...
```

### Frontmatter Schema (exact format for run.md)

```yaml
---
run_id: "2026-02-10-abc123"
youtube_url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
current_stage: "research"
current_attempt: 1
qa_status: "pending"
stages_completed:
  - "router"
escalation_state: "none"
best_of_three_overrides: []
created_at: "2026-02-10T14:00:00+00:00"
updated_at: "2026-02-10T14:05:00+00:00"
---
```

Key serialization rules:
- Enums → `.value` strings (snake_case lowercase)
- Tuples → YAML lists
- RunId → plain string
- QAStatus.PENDING → `"pending"`
- Empty tuples → `[]`

### Atomic Write Pattern (from architecture.md)

```python
async def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    async with aiofiles.open(tmp, "w") as f:
        await f.write(content)
    tmp.rename(path)  # atomic on POSIX same-filesystem
```

### Checkpoint Timing Rules

- Write AFTER each stage completes (not during)
- Write BEFORE QA gate starts (captures artifact to be reviewed)
- Never checkpoint mid-agent-execution (incomplete state)

### File Layout for Runs

```
workspace/runs/
├── 2026-02-10-abc123/
│   └── run.md              ← State file (frontmatter + optional log)
├── 2026-02-10-def456/
│   └── run.md
```

### dataclasses.replace() Pattern

Since RunState is `frozen=True`, you CANNOT mutate fields. Use `dataclasses.replace()`:

```python
from dataclasses import replace
from datetime import datetime, timezone

new_state = replace(
    state,
    current_stage=next_stage,
    stages_completed=state.stages_completed + (state.current_stage.value,),
    current_attempt=1,
    qa_status=QAStatus.PENDING,
    updated_at=datetime.now(timezone.utc).isoformat(),
)
```

### Testing Patterns

- **State machine tests**: Pure unit tests, no mocks needed. Create RunState → call apply_transition → assert new RunState fields.
- **FileStateStore tests**: Integration tests using `tmp_path` fixture. Real filesystem I/O.
- **Both**: Use `sample_run_state` fixture from `conftest.py`.
- **Async tests**: `pytest-asyncio` with `asyncio_mode = "auto"` — just mark tests `async def`.

### Project Environment Notes (from Story 1.1)

- Python 3.13.5 in Docker container (targeting >=3.11)
- Poetry 2.3.2 at `/home/umbrel/.local/bin/poetry`
- Run mypy WITHOUT path arg: `poetry run mypy` (uses pyproject.toml `packages = ["pipeline"]`)
- Run tests: `poetry run pytest tests/ -v --tb=short`
- src layout: `[[tool.poetry.packages]]` with `include = "pipeline"`, `from = "src"`

### References

- [Source: architecture.md#Core Architectural Decisions] — State Pattern FSM, file-based persistence
- [Source: architecture.md#Data Architecture] — Run state as markdown frontmatter, atomic write pattern
- [Source: architecture.md#Implementation Patterns] — Atomic state writes, checkpoint timing
- [Source: architecture.md#Application Layer] — state_machine.py, orchestrator.py design
- [Source: architecture.md#Infrastructure Adapters] — file_state_store.py, frontmatter read/write
- [Source: architecture.md#Project Structure] — File paths and module locations
- [Source: epics.md#Story 1.2] — Original acceptance criteria, FR35/FR40
- [Source: 1-1-project-scaffolding-domain-model.md] — Previous story learnings, established patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- `ruff check` flagged UP017 (`timezone.utc` → `datetime.UTC`) and UP015 (unnecessary `"r"` mode arg) — auto-fixed with `ruff check --fix`
- `mypy` required `types-PyYAML` and `types-aiofiles` stubs — added via `poetry add --group dev`
- `black` reformatted `state_machine.py` and `test_file_state_store.py` — auto-fixed

### Completion Notes List

- All 6 tasks completed. 128 tests passing, 97.02% coverage, all linters + mypy clean.
- PipelineStateMachine handles 7 event types with full bookkeeping (stages_completed, current_attempt, qa_status, escalation_state, updated_at).
- Frontmatter serialization handles enum ↔ value, tuple ↔ list, RunId ↔ str round-trips.
- FileStateStore uses atomic write (write .tmp then rename) with aiofiles for async I/O.
- 22 unit tests for state machine, 19 integration tests for file store + frontmatter serialization.

### Senior Developer Review (AI)

**Reviewed by:** Claude Opus 4.6 + Gemini 2.5 Pro (external expert)
**Date:** 2026-02-11
**Outcome:** Approved after fixes

**Issues found and fixed (8 total):**
- **H1** (fixed): `deserialize_run_state` raised raw `KeyError` on missing fields → wrapped in `try/except KeyError`, raises `ValueError`
- **H2** (fixed): `save_state` left orphan `.tmp` on write failure → added `try/except` with `.unlink()` cleanup
- **H3** (fixed): `list_incomplete_runs` aborted on any corrupt file → added `try/except (ValueError, OSError)` with `logging.warning`, continues
- **M1** (fixed): No test for `save_state` overwrite → added `test_save_overwrites_existing_state`
- **M2** (fixed): `split("---")` fragile → changed to `split("---", 2)` with `startswith("---")` guard
- **M3** (fixed): `next_stage` looked up unconditionally → moved into branches that use it
- **L1** (deferred): Events as bare strings — design debt, deferred to future story (touches domain layer)
- **L2** (fixed): No protocol compliance check → added `TYPE_CHECKING` guard with `StateStorePort` assertion

**Post-fix validation:** 128 tests, 97.02% coverage, mypy clean, all linters clean.

### File List

- `src/pipeline/application/state_machine.py` — PipelineStateMachine class (validate_transition, apply_transition)
- `src/pipeline/infrastructure/adapters/frontmatter.py` — serialize_run_state, deserialize_run_state
- `src/pipeline/infrastructure/adapters/file_state_store.py` — FileStateStore (save_state, load_state, list_incomplete_runs)
- `tests/unit/application/test_state_machine.py` — 22 unit tests for PipelineStateMachine
- `tests/integration/test_file_state_store.py` — 19 integration tests for FileStateStore + frontmatter
