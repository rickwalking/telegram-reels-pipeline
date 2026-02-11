# Story 9.2: Wire PipelineRunner into Orchestrator

Status: ready-for-dev

## Story

As a developer,
I want PipelineRunner, StageRunner, and DeliveryHandler instantiated in bootstrap and available on the Orchestrator,
So that main.py can call pipeline execution instead of a stub.

## Acceptance Criteria

1. **Given** `create_orchestrator()` is called,
   **When** the Orchestrator is returned,
   **Then** it contains a fully-wired `PipelineRunner` field,
   **And** PipelineRunner has StageRunner, StateStore, EventBus, and DeliveryHandler injected.

2. **Given** `StageRunner` is instantiated in bootstrap,
   **When** it is wired,
   **Then** it receives `AgentExecutionPort` (CliBackend), `RecoveryChain`, `ReflectionLoop`, and `EventBus`.

3. **Given** `DeliveryHandler` is instantiated in bootstrap,
   **When** Telegram is configured,
   **Then** DeliveryHandler receives `MessagingPort` (TelegramBotAdapter) and `FileDeliveryPort` (GoogleDriveAdapter),
   **And** when Telegram is not configured, DeliveryHandler is None.

4. **Given** `PipelineRunner` needs a `workflows_dir` path,
   **When** instantiated,
   **Then** it points to `{project_root}/workflows/` (the BMAD workflow directory, NOT inside workspace).

5. **Given** all wiring is complete,
   **When** I run the full test suite,
   **Then** all existing tests pass and bootstrap tests verify the new fields exist.

## Tasks / Subtasks

- [ ] Task 1: Add PipelineRunner + StageRunner + DeliveryHandler to Orchestrator dataclass (AC: #1, #2, #3)
  - [ ] Add `pipeline_runner: PipelineRunner | None = field(default=None)` to Orchestrator
  - [ ] Add `stage_runner: StageRunner | None = field(default=None)` to Orchestrator
  - [ ] Add `delivery_handler: DeliveryHandler | None = field(default=None)` to Orchestrator
  - [ ] Import all three classes in bootstrap.py

- [ ] Task 2: Instantiate StageRunner in create_orchestrator() (AC: #2)
  - [ ] Actual constructor: `StageRunner(reflection_loop=reflection_loop, recovery_chain=recovery_chain, event_bus=event_bus)`
  - [ ] NOTE: StageRunner does NOT take `agent_port` — ReflectionLoop already wraps CliBackend
  - [ ] Verify constructor signature in `application/stage_runner.py:31`

- [ ] Task 3: Instantiate DeliveryHandler conditionally (AC: #3)
  - [ ] Actual constructor: `DeliveryHandler(messaging=telegram_bot, file_delivery=google_drive_adapter)`
  - [ ] `file_delivery` param is `FileDeliveryPort | None = None` (optional)
  - [ ] GoogleDriveAdapter needs credentials path from settings — add `google_drive_credentials_path` to PipelineSettings if not present (dependency on 9.4)
  - [ ] If Telegram not configured: `delivery_handler = None`
  - [ ] If Telegram configured but no Drive creds: `DeliveryHandler(messaging=telegram_bot)` (no file_delivery)

- [ ] Task 4: Instantiate PipelineRunner (AC: #1, #4)
  - [ ] Determine `workflows_dir` path: should be `Path(__file__).resolve().parent.parent.parent.parent / "workflows"` or from settings
  - [ ] `PipelineRunner(stage_runner=stage_runner, state_store=state_store, event_bus=event_bus, delivery_handler=delivery_handler, workflows_dir=workflows_dir)`

- [ ] Task 5: Add workflows_dir to PipelineSettings (AC: #4)
  - [ ] Add `workflows_dir: Path` field to `PipelineSettings` in `settings.py`
  - [ ] Default to project root's `workflows/` directory
  - [ ] This path is where `stages/`, `qa/gate-criteria/`, and `revision-flows/` live

- [ ] Task 6: Test and validate (AC: #5)
  - [ ] Add bootstrap test: `create_orchestrator()` returns Orchestrator with `pipeline_runner` not None
  - [ ] Run full test suite
  - [ ] Run linters (ruff, mypy, black)

## Dev Notes

### Key Dependencies

PipelineRunner needs these components already wired:
- `StageRunner` — drives individual stages (execute agent + QA + recovery)
- `StateStorePort` — FileStateStore (already wired)
- `EventBus` — already wired
- `DeliveryHandler` — sends final video + content via Telegram/Drive

StageRunner constructor (from `stage_runner.py:31`):
```python
def __init__(self, reflection_loop: ReflectionLoop, recovery_chain: RecoveryChain, event_bus: EventBus) -> None:
```
- `ReflectionLoop` — already wired (wraps CliBackend internally)
- `RecoveryChain` — already wired
- `EventBus` — already wired
- NOTE: StageRunner does NOT take AgentExecutionPort — it goes through ReflectionLoop

DeliveryHandler constructor (from `delivery_handler.py:44`):
```python
def __init__(self, messaging: MessagingPort, file_delivery: FileDeliveryPort | None = None) -> None:
```
- `MessagingPort` — TelegramBotAdapter (already wired, optional)
- `FileDeliveryPort` — GoogleDriveAdapter (needs instantiation, optional)

### Dependency on Story 9.4

GoogleDriveAdapter requires a credentials path. If `PipelineSettings` doesn't yet have `google_drive_credentials_path`, that field must be added (in 9.4 or here). Wire Drive adapter only when credentials path is configured and exists.

### workflows_dir Path Resolution

PipelineRunner reads files from:
- `workflows/stages/stage-01-router.md` through `stage-08-delivery.md`
- `workflows/qa/gate-criteria/{gate}-criteria.md`

These are BMAD content files (populated in Epics 7-8), not Python source. The path should resolve relative to the project root (`telegram-reels-pipeline/`), not the Python package.

### Existing File Locations

```
src/pipeline/application/pipeline_runner.py   # PipelineRunner class
src/pipeline/application/stage_runner.py       # StageRunner class
src/pipeline/application/delivery_handler.py   # DeliveryHandler class
src/pipeline/app/bootstrap.py                  # Orchestrator + create_orchestrator()
src/pipeline/app/settings.py                   # PipelineSettings
src/pipeline/infrastructure/adapters/google_drive_adapter.py  # GoogleDriveAdapter
```

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 4] — PipelineRunner never instantiated
- [Source: pipeline_runner.py] — PipelineRunner constructor signature
- [Source: bootstrap.py] — Current Orchestrator fields

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
