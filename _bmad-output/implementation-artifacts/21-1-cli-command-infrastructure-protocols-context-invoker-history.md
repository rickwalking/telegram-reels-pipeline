# Story 21.1: CLI Command Infrastructure — Protocols, Context, Invoker, History

Status: ready-for-dev

## Story

As a pipeline developer,
I want a Command pattern infrastructure with protocols, a shared context, an invoker, and command history,
so that the CLI has a scalable, testable foundation where each concern is isolated and all executions are traceable.

## Acceptance Criteria

1. New package `src/pipeline/application/cli/` with `protocols.py`, `context.py`, `invoker.py`, `history.py`
2. `protocols.py` defines `Command` protocol (with `name` property + `async execute(context) -> CommandResult`), `StageHook` protocol (`should_run(stage, phase) -> bool` + `async execute(context) -> None`), `InputReader` protocol (abstracts stdin), `ClipDurationProber` protocol (abstracts ffprobe)
3. `context.py` defines `PipelineContext` dataclass holding: workspace, artifacts, settings, stage_runner, event_bus, and accumulated state — replaces the 11-argument `run_pipeline()` signature
4. `invoker.py` defines `PipelineInvoker` that executes commands, records results in `CommandHistory`, catches/records exceptions with status `failed`, re-raises
5. `history.py` defines `CommandHistory` — debug stack persisted to `command-history.json` via atomic write, queryable (list all, filter by status, get last N)
6. `domain/models.py` extended with `CommandRecord` frozen dataclass
7. `infrastructure/adapters/ffprobe_adapter.py` implements `ClipDurationProber` protocol
8. `infrastructure/adapters/stdin_reader.py` implements `InputReader` protocol
9. No source file exceeds 500 lines
10. Comprehensive tests for all new modules

## Tasks / Subtasks

- [ ] Task 1: Create `application/cli/` package structure (AC: #1)
  - [ ] 1.1 Create `src/pipeline/application/cli/__init__.py`
  - [ ] 1.2 Create `tests/unit/application/cli/__init__.py`
- [ ] Task 2: Define protocols in `protocols.py` (AC: #2)
  - [ ] 2.1 `Command` protocol with `name: str` property + `async execute(context: PipelineContext) -> CommandResult`
  - [ ] 2.2 `CommandResult` frozen dataclass (success: bool, message: str, data: Mapping)
  - [ ] 2.3 `StageHook` protocol with `should_run(stage: PipelineStage, phase: Literal["pre", "post"]) -> bool` + `async execute(context: PipelineContext) -> None`
  - [ ] 2.4 `InputReader` protocol with `async read(prompt: str, timeout: int) -> str | None`
  - [ ] 2.5 `ClipDurationProber` protocol with `async probe(clip_path: Path) -> float | None`
- [ ] Task 3: Define `CommandRecord` in `domain/models.py` (AC: #6)
  - [ ] 3.1 Frozen dataclass: `name: str`, `started_at: str`, `finished_at: str`, `status: str`, `error: str | None`
  - [ ] 3.2 Use `tuple` for any collection fields per project conventions
- [ ] Task 4: Implement `PipelineContext` in `context.py` (AC: #3)
  - [ ] 4.1 Dataclass holding: workspace (Path | None), artifacts (tuple[Path, ...]), settings (PipelineSettings), stage_runner, event_bus, plus mutable accumulated state
  - [ ] 4.2 Type-safe property accessors for optional fields
  - [ ] 4.3 Method to snapshot current state for history recording
- [ ] Task 5: Implement `CommandHistory` in `history.py` (AC: #5)
  - [ ] 5.1 Append `CommandRecord` to internal stack
  - [ ] 5.2 `persist(workspace: Path)` — atomic write to `command-history.json`
  - [ ] 5.3 Query methods: `all()`, `by_status(status)`, `last(n)`
  - [ ] 5.4 Handle missing workspace gracefully (log warning, skip persist)
- [ ] Task 6: Implement `PipelineInvoker` in `invoker.py` (AC: #4)
  - [ ] 6.1 Constructor receives `CommandHistory`
  - [ ] 6.2 `async execute(command, context)` — records start time, calls command.execute, records end time + result, persists history
  - [ ] 6.3 On exception: record status=`failed` with error message, persist, re-raise
  - [ ] 6.4 Always persist history (even on failure) via finally block
- [ ] Task 7: Implement `FfprobeAdapter` in `infrastructure/adapters/ffprobe_adapter.py` (AC: #7)
  - [ ] 7.1 Extract `_probe_clip_duration` logic from `scripts/run_cli.py`
  - [ ] 7.2 Implement `ClipDurationProber` protocol
  - [ ] 7.3 Async subprocess call to ffprobe with timeout
  - [ ] 7.4 Graceful None return on failure (OSError, ValueError, non-zero exit)
- [ ] Task 8: Implement `StdinReader` in `infrastructure/adapters/stdin_reader.py` (AC: #8)
  - [ ] 8.1 Extract `_timed_input` logic from `scripts/run_cli.py`
  - [ ] 8.2 Implement `InputReader` protocol
  - [ ] 8.3 `asyncio.to_thread(input, prompt)` with `asyncio.wait_for` timeout
  - [ ] 8.4 Return None on timeout/EOF/KeyboardInterrupt
- [ ] Task 9: Write comprehensive tests (AC: #10)
  - [ ] 9.1 `tests/unit/application/cli/test_invoker.py` — happy path, exception recording, history persistence, re-raise behavior
  - [ ] 9.2 `tests/unit/application/cli/test_history.py` — append, persist atomic write, query methods, empty history, missing workspace
  - [ ] 9.3 `tests/unit/application/cli/test_context.py` — construction, snapshot, optional fields
  - [ ] 9.4 `tests/unit/domain/test_command_record.py` — frozen dataclass, immutability, fields
  - [ ] 9.5 `tests/unit/infrastructure/test_ffprobe_adapter.py` — success, non-zero exit, invalid output, OSError, timeout
  - [ ] 9.6 `tests/unit/infrastructure/test_stdin_reader.py` — normal input, EOF, KeyboardInterrupt, timeout
- [ ] Task 10: Verify 500-line limit on all source files (AC: #9)

## Dev Notes

### Architecture Compliance

**Layer placement:**
- `application/cli/protocols.py` — application layer (protocols reference domain types like `PipelineStage`)
- `application/cli/context.py` — application layer (holds application-layer objects like StageRunner, EventBus)
- `application/cli/invoker.py` — application layer (orchestrates command execution)
- `application/cli/history.py` — application layer (manages command records, uses atomic write)
- `domain/models.py` — domain layer (CommandRecord is a pure frozen dataclass, stdlib only)
- `infrastructure/adapters/ffprobe_adapter.py` — infrastructure layer (external subprocess dependency)
- `infrastructure/adapters/stdin_reader.py` — infrastructure layer (external stdin dependency)

**Import rules:**
- `protocols.py` imports from `domain.models`, `domain.enums` — OK (application imports domain)
- `context.py` uses `TYPE_CHECKING` guards for `EventBus`, `StageRunner`, `PipelineSettings` imports
- `invoker.py` imports `Command` protocol from `protocols.py` — OK (same layer)
- `history.py` imports `CommandRecord` from `domain.models` — OK (application imports domain)
- Infrastructure adapters import stdlib only + domain types — OK

### Existing Patterns to Follow

**Frozen dataclass pattern** (from `domain/models.py`):
```python
@dataclass(frozen=True)
class CommandRecord:
    name: str
    started_at: str
    finished_at: str
    status: str  # "success" | "failed"
    error: str | None = None
```

**Protocol pattern** (from `domain/ports.py`):
```python
@runtime_checkable
class Command(Protocol):
    @property
    def name(self) -> str: ...
    async def execute(self, context: PipelineContext) -> CommandResult: ...
```

**Adapter pattern** (from `infrastructure/adapters/`):
```python
class FfprobeAdapter:
    if TYPE_CHECKING:
        _protocol_check: ClipDurationProber

    async def probe(self, clip_path: Path) -> float | None:
        # asyncio.create_subprocess_exec("ffprobe", ...)
```

**Atomic write pattern** (from `file_state_store.py` and across codebase):
```python
fd, tmp_path_str = tempfile.mkstemp(dir=workspace, suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path_str, target_path)
except BaseException:
    with contextlib.suppress(OSError):
        os.unlink(tmp_path_str)
    raise
```

**Test factory pattern** (from `test_stage_runner.py`):
```python
def _make_invoker(
    history: CommandHistory | None = None,
) -> PipelineInvoker:
    if history is None:
        history = CommandHistory()
    return PipelineInvoker(history=history)
```

### Critical Constraints

- `except Exception: pass` is **BANNED** — always log or re-raise
- Exception chaining: always `raise X from Y`
- Line length: 120 chars max
- Async for I/O; synchronous for pure transforms
- No file exceeds 500 lines
- `CommandRecord` in domain — stdlib only, no Pydantic

### Project Structure Notes

New files to create:
```
src/pipeline/application/cli/
├── __init__.py
├── protocols.py       # Command, CommandResult, StageHook, InputReader, ClipDurationProber
├── context.py         # PipelineContext
├── invoker.py         # PipelineInvoker
└── history.py         # CommandHistory

src/pipeline/infrastructure/adapters/
├── ffprobe_adapter.py # FfprobeAdapter (NEW)
└── stdin_reader.py    # StdinReader (NEW)

tests/unit/application/cli/
├── __init__.py
├── test_invoker.py
├── test_history.py
└── test_context.py

tests/unit/domain/
└── test_command_record.py (add to existing test files or new)

tests/unit/infrastructure/
├── test_ffprobe_adapter.py
└── test_stdin_reader.py
```

Existing files to modify:
```
src/pipeline/domain/models.py          # Add CommandRecord
src/pipeline/application/__init__.py   # Ensure cli subpackage importable
```

### References

- [Source: src/pipeline/domain/models.py] — Frozen dataclass patterns, tuple/Mapping conventions
- [Source: src/pipeline/domain/ports.py] — Protocol definitions, @runtime_checkable pattern
- [Source: src/pipeline/application/event_bus.py] — EventBus structure (will be in PipelineContext)
- [Source: src/pipeline/application/stage_runner.py] — StageRunner constructor injection pattern
- [Source: src/pipeline/application/workspace_manager.py] — WorkspaceManager pattern
- [Source: src/pipeline/infrastructure/adapters/file_state_store.py] — Atomic write pattern
- [Source: src/pipeline/infrastructure/adapters/proc_resource_monitor.py] — asyncio.to_thread adapter pattern
- [Source: src/pipeline/app/bootstrap.py] — DI wiring pattern (Orchestrator dataclass)
- [Source: src/pipeline/app/settings.py] — PipelineSettings fields
- [Source: scripts/run_cli.py:113-136] — _probe_clip_duration to extract into FfprobeAdapter
- [Source: scripts/run_cli.py:410-422] — _timed_input to extract into StdinReader
- [Source: tests/unit/application/test_stage_runner.py] — Test factory helper pattern
- [Source: tests/unit/application/test_event_bus.py] — AsyncMock test pattern

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
