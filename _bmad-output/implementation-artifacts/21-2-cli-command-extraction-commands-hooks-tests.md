# Story 21.2: CLI Command Extraction — Commands, Hooks, Comprehensive Tests

Status: ready-for-dev

## Story

As a pipeline developer,
I want each CLI concern extracted into its own ConcreteCommand and StageHook file with dependency injection,
so that every piece of logic is independently testable, no source file exceeds 500 lines, and the original `run_cli.py` becomes a thin composition root.

## Acceptance Criteria

1. Each command in its own file under `application/cli/commands/`:
   - `validate_args.py` — `ValidateArgsCommand`
   - `setup_workspace.py` — `SetupWorkspaceCommand`
   - `download_cutaways.py` — `DownloadCutawaysCommand`
   - `run_elicitation.py` — `RunElicitationCommand`
   - `run_stage.py` — `RunStageCommand`
   - `run_pipeline.py` — `RunPipelineCommand`
2. Each hook in its own file under `application/cli/hooks/`:
   - `veo3_fire_hook.py` — `Veo3FireHook`
   - `veo3_await_hook.py` — `Veo3AwaitHook`
   - `manifest_hook.py` — `ManifestBuildHook`
   - `encoding_hook.py` — `EncodingPlanHook`
3. Each hook implements `StageHook` protocol with `should_run()` self-selection
4. All commands receive dependencies through constructor injection (protocols, not implementations)
5. `scripts/run_cli.py` becomes a thin composition root (~100 lines): parse args, instantiate adapters, inject into commands, hand to invoker — zero business logic
6. No source file in `src/` or `scripts/` exceeds 500 lines (test files exempt)
7. Every command has its own test file in `tests/unit/application/cli/commands/`
8. Every hook has its own test file in `tests/unit/application/cli/hooks/`
9. Every branch covered: happy path, validation failures, partial failures, timeouts, non-interactive fallback, resume detection, empty workspace, all-stages-complete
10. All tests use fakes/stubs for dependencies (protocols, not concrete classes)
11. Existing test behavior from `test_run_cli.py`, `test_cli_cutaway.py`, `test_run_cli_atomic_write.py` preserved and reorganized

## Tasks / Subtasks

- [ ] Task 1: Create package structure (AC: #1, #2)
  - [ ] 1.1 Create `src/pipeline/application/cli/commands/__init__.py`
  - [ ] 1.2 Create `src/pipeline/application/cli/hooks/__init__.py`
  - [ ] 1.3 Create `tests/unit/application/cli/commands/__init__.py`
  - [ ] 1.4 Create `tests/unit/application/cli/hooks/__init__.py`

- [ ] Task 2: Extract `ValidateArgsCommand` (AC: #1, #4)
  - [ ] 2.1 Create `commands/validate_args.py` with `ValidateArgsCommand`
  - [ ] 2.2 Extract from `run_cli.py`: `_validate_cli_args()` (L289-327), `_resolve_start_stage()` (L259-286), `_detect_resume_stage()` (L240-256), `STAGE_SIGNATURES` (L229-237), `compute_moments_requested()` (L69-84)
  - [ ] 2.3 Constructor receives: no external deps (pure validation)
  - [ ] 2.4 `execute(context)` validates context fields, sets `context.state["start_stage"]`, `context.state["moments_requested"]`

- [ ] Task 3: Extract `SetupWorkspaceCommand` (AC: #1, #4)
  - [ ] 3.1 Create `commands/setup_workspace.py` with `SetupWorkspaceCommand`
  - [ ] 3.2 Extract from `run_cli.py`: workspace creation (L910-940), resume detection (L936-940), preflight printing (L336-349)
  - [ ] 3.3 Constructor receives: `WorkspaceManager` protocol or factory
  - [ ] 3.4 `execute(context)` creates/resumes workspace, sets `context.workspace`, loads existing artifacts

- [ ] Task 4: Extract `DownloadCutawaysCommand` (AC: #1, #4)
  - [ ] 4.1 Create `commands/download_cutaways.py` with `DownloadCutawaysCommand`
  - [ ] 4.2 Extract from `run_cli.py`: `_parse_cutaway_spec()` (L87-110), `_download_cutaway_clips()` (L139-212), `_maybe_download_cutaways()` (L215-224)
  - [ ] 4.3 Constructor receives: `ClipDurationProber` protocol, `ExternalClipDownloaderPort` protocol
  - [ ] 4.4 `execute(context)` downloads clips, writes manifest, updates `context.state`

- [ ] Task 5: Extract `RunElicitationCommand` (AC: #1, #4)
  - [ ] 5.1 Create `commands/run_elicitation.py` with `RunElicitationCommand`
  - [ ] 5.2 Extract from `run_cli.py`: `_run_router_with_elicitation()` (L503-576), `_collect_elicitation_answers()` (L436-454), `_save_elicitation_context()` (L457-477), `_extract_elicitation_questions()` (L480-500), `_validate_questions()` (L425-433), `_find_router_output()` (L357-389), `_parse_router_output()` (L392-407), `_is_interactive()` (L352-354)
  - [ ] 5.3 Constructor receives: `InputReader` protocol, `StageRunner`, constants (max rounds, max questions, mtime tolerance)
  - [ ] 5.4 `execute(context)` runs router with elicitation loop, returns result

- [ ] Task 6: Extract `RunStageCommand` (AC: #1, #3, #4)
  - [ ] 6.1 Create `commands/run_stage.py` with `RunStageCommand`
  - [ ] 6.2 Extract from `run_cli.py`: single-stage execution from `_run_stages()` (L717-849)
  - [ ] 6.3 Constructor receives: `StageRunner`, `tuple[StageHook, ...]` for pre/post hooks
  - [ ] 6.4 `execute(context)` runs a single stage through reflection loop, fires pre/post hooks via `should_run()` self-selection
  - [ ] 6.5 `_stage_name()` (L329-333) as static utility

- [ ] Task 7: Extract hooks (AC: #2, #3)
  - [ ] 7.1 Create `hooks/veo3_fire_hook.py` with `Veo3FireHook` — extract `_fire_veo3_background()` (L587-616), fires post-Content
  - [ ] 7.2 Create `hooks/veo3_await_hook.py` with `Veo3AwaitHook` — extract `_run_veo3_await_gate()` (L619-664), fires pre-Assembly
  - [ ] 7.3 Create `hooks/manifest_hook.py` with `ManifestBuildHook` — extract `_build_cutaway_manifest()` (L667-714), fires pre-Assembly
  - [ ] 7.4 Create `hooks/encoding_hook.py` with `EncodingPlanHook` — extract FFmpeg encoding plan execution (L823-836 in `_run_stages()`), fires post-FFmpeg

- [ ] Task 8: Extract `RunPipelineCommand` (AC: #1, #4)
  - [ ] 8.1 Create `commands/run_pipeline.py` with `RunPipelineCommand`
  - [ ] 8.2 Orchestrates: ValidateArgs → SetupWorkspace → DownloadCutaways → (RunStage × N) via `PipelineInvoker`
  - [ ] 8.3 Constructor receives: `PipelineInvoker`, sub-commands, `tuple[StageHook, ...]`
  - [ ] 8.4 `execute(context)` is the top-level pipeline orchestration

- [ ] Task 9: Rewrite `scripts/run_cli.py` as thin composition root (AC: #5)
  - [ ] 9.1 Keep only: `main()` with argparse, adapter instantiation, DI wiring, `asyncio.run()`
  - [ ] 9.2 Import commands and hooks, inject dependencies, hand to `RunPipelineCommand`
  - [ ] 9.3 Target ~100 lines, zero business logic
  - [ ] 9.4 Verify `run_cli.py` < 500 lines

- [ ] Task 10: Write command tests (AC: #7, #9, #10)
  - [ ] 10.1 `tests/unit/application/cli/commands/test_validate_args.py` — arg validation, defaults, resume detection, moments computation
  - [ ] 10.2 `tests/unit/application/cli/commands/test_setup_workspace.py` — create/resume workspace, preflight
  - [ ] 10.3 `tests/unit/application/cli/commands/test_download_cutaways.py` — parsing, download, manifest, partial failures, atomic write
  - [ ] 10.4 `tests/unit/application/cli/commands/test_run_elicitation.py` — interactive loop, non-interactive, max rounds, question validation
  - [ ] 10.5 `tests/unit/application/cli/commands/test_run_stage.py` — single stage, hook firing, escalation
  - [ ] 10.6 `tests/unit/application/cli/commands/test_run_pipeline.py` — full orchestration, partial completion

- [ ] Task 11: Write hook tests (AC: #8, #9, #10)
  - [ ] 11.1 `tests/unit/application/cli/hooks/test_veo3_fire_hook.py` — should_run targeting, background task, no-adapter fallback
  - [ ] 11.2 `tests/unit/application/cli/hooks/test_veo3_await_hook.py` — should_run targeting, await logic, timeout, no-task fallback
  - [ ] 11.3 `tests/unit/application/cli/hooks/test_manifest_hook.py` — should_run targeting, manifest building, missing files
  - [ ] 11.4 `tests/unit/application/cli/hooks/test_encoding_hook.py` — should_run targeting, FFmpeg execution, plan parsing

- [ ] Task 12: Migrate existing tests (AC: #11)
  - [ ] 12.1 Verify all 89 tests from `test_run_cli.py` are covered by new command tests
  - [ ] 12.2 Verify all 31 tests from `test_cli_cutaway.py` are covered by new command tests
  - [ ] 12.3 Verify all 2 tests from `test_run_cli_atomic_write.py` are covered
  - [ ] 12.4 Remove old test files after verification passes
  - [ ] 12.5 Run full test suite to confirm no regressions

- [ ] Task 13: Verify constraints (AC: #6)
  - [ ] 13.1 No source file in `src/` exceeds 500 lines
  - [ ] 13.2 `scripts/run_cli.py` under 500 lines
  - [ ] 13.3 All linting passes (ruff, mypy)
  - [ ] 13.4 Full test suite passes

## Dev Notes

### Architecture Compliance

**Layer placement:**
- `application/cli/commands/*.py` — application layer (orchestrate domain + infra via protocols)
- `application/cli/hooks/*.py` — application layer (stage lifecycle hooks)
- `scripts/run_cli.py` — app layer equivalent (composition root, wires everything)

**Import rules:**
- Commands import from `application/cli/protocols`, `application/cli/context` — OK (same layer)
- Commands use `TYPE_CHECKING` guards for infra-layer types (adapters, settings)
- Hooks import from `application/cli/protocols` — OK (same layer)
- `run_cli.py` imports from all layers — OK (app layer)

### Extraction Map — `run_cli.py` Functions → New Locations

| Function | Lines | Target File |
|----------|-------|-------------|
| `compute_moments_requested()` | 69-84 | `commands/validate_args.py` |
| `_parse_cutaway_spec()` | 87-110 | `commands/download_cutaways.py` |
| `_probe_clip_duration()` | 113-136 | **Already extracted** → `FfprobeAdapter` (Story 21.1) |
| `_download_cutaway_clips()` | 139-212 | `commands/download_cutaways.py` |
| `_maybe_download_cutaways()` | 215-224 | `commands/download_cutaways.py` |
| `STAGE_SIGNATURES` | 229-237 | `commands/validate_args.py` |
| `_detect_resume_stage()` | 240-256 | `commands/validate_args.py` |
| `_resolve_start_stage()` | 259-286 | `commands/validate_args.py` |
| `_validate_cli_args()` | 289-327 | `commands/validate_args.py` |
| `_stage_name()` | 329-333 | `commands/run_stage.py` (static utility) |
| `_print_resume_preflight()` | 336-349 | `commands/setup_workspace.py` |
| `_is_interactive()` | 352-354 | `commands/run_elicitation.py` |
| `_find_router_output()` | 357-389 | `commands/run_elicitation.py` |
| `_parse_router_output()` | 392-407 | `commands/run_elicitation.py` |
| `_timed_input()` | 410-422 | **Already extracted** → `StdinReader` (Story 21.1) |
| `_validate_questions()` | 425-433 | `commands/run_elicitation.py` |
| `_collect_elicitation_answers()` | 436-454 | `commands/run_elicitation.py` |
| `_save_elicitation_context()` | 457-477 | `commands/run_elicitation.py` |
| `_extract_elicitation_questions()` | 480-500 | `commands/run_elicitation.py` |
| `_run_router_with_elicitation()` | 503-576 | `commands/run_elicitation.py` |
| `_build_veo3_adapter()` | 579-584 | `scripts/run_cli.py` (composition root) |
| `_fire_veo3_background()` | 587-616 | `hooks/veo3_fire_hook.py` |
| `_run_veo3_await_gate()` | 619-664 | `hooks/veo3_await_hook.py` |
| `_build_cutaway_manifest()` | 667-714 | `hooks/manifest_hook.py` |
| `_run_stages()` | 717-849 | Split across `RunStageCommand` + `RunPipelineCommand` |
| `_print_stage_result()` | 852-865 | `commands/run_stage.py` |
| `run_pipeline()` | 868-991 | `commands/run_pipeline.py` + `scripts/run_cli.py` |
| `main()` | 993-1049 | `scripts/run_cli.py` (stays, argparse only) |

### Test Migration Map

| Old Test File | Tests | New Test File |
|--------------|-------|---------------|
| `test_run_cli.py::TestIsInteractive` | 3 | `test_run_elicitation.py` |
| `test_run_cli.py::TestFindRouterOutput` | 6 | `test_run_elicitation.py` |
| `test_run_cli.py::TestParseRouterOutput` | 5 | `test_run_elicitation.py` |
| `test_run_cli.py::TestValidateQuestions` | 6 | `test_run_elicitation.py` |
| `test_run_cli.py::TestTimedInput` | 4 | (**covered by Story 21.1** `test_stdin_reader.py`) |
| `test_run_cli.py::TestCollectElicitationAnswers` | 4 | `test_run_elicitation.py` |
| `test_run_cli.py::TestSaveElicitationContext` | 2 | `test_run_elicitation.py` |
| `test_run_cli.py::TestExtractElicitationQuestions` | 6 | `test_run_elicitation.py` |
| `test_run_cli.py::TestRunRouterWithElicitation` | 7 | `test_run_elicitation.py` |
| `test_run_cli.py::TestDetectResumeStage` | 6 | `test_validate_args.py` |
| `test_run_cli.py::TestValidateCliArgs` | 22 | `test_validate_args.py` |
| `test_run_cli.py::TestStageName` | 3 | `test_run_stage.py` |
| `test_run_cli.py::TestPrintResumePreflight` | 2 | `test_setup_workspace.py` |
| `test_run_cli.py::TestStyleArgument` | 8 | `test_validate_args.py` |
| `test_cli_cutaway.py::TestParseCutawaySpec` | 11 | `test_download_cutaways.py` |
| `test_cli_cutaway.py::TestProbeClipDuration` | 5 | (**covered by Story 21.1** `test_ffprobe_adapter.py`) |
| `test_cli_cutaway.py::TestDownloadCutawayClips` | 10 | `test_download_cutaways.py` |
| `test_cli_cutaway.py::TestCutawayArgparse` | 5 | `test_validate_args.py` |
| `test_run_cli_atomic_write.py` | 2 | `test_download_cutaways.py` |

### Existing Patterns to Follow

**Command implementation pattern** (from Story 21.1 protocols):
```python
class ValidateArgsCommand:
    if TYPE_CHECKING:
        _protocol_check: Command

    @property
    def name(self) -> str:
        return "validate-args"

    async def execute(self, context: PipelineContext) -> CommandResult:
        # Pure validation, no I/O
        ...
```

**Hook self-selection pattern:**
```python
class Veo3FireHook:
    if TYPE_CHECKING:
        _protocol_check: StageHook

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        return stage == PipelineStage.CONTENT and phase == "post"

    async def execute(self, context: PipelineContext) -> None:
        # Fire Veo3 background task
        ...
```

**DI constructor pattern** (commands depend on protocols, not implementations):
```python
class DownloadCutawaysCommand:
    def __init__(
        self,
        clip_downloader: ExternalClipDownloaderPort,
        duration_prober: ClipDurationProber,
    ) -> None:
        self._clip_downloader = clip_downloader
        self._duration_prober = duration_prober
```

### Critical Constraints

- `except Exception: pass` is **BANNED** — always log or re-raise
- Exception chaining: always `raise X from Y`
- Line length: 120 chars max
- Async for I/O; synchronous for pure transforms
- No source file exceeds 500 lines (test files exempt)
- Commands depend on protocols, not concrete implementations
- Hooks use `should_run()` self-selection, no if/elif chains in stage runner

### Constants to Preserve

```python
ALL_STAGES = (...)          # Stage pipeline spec
DEFAULT_URL = "..."         # Default YouTube URL
MAX_ELICITATION_ROUNDS = 2
MAX_QUESTIONS_PER_ROUND = 5
INPUT_TIMEOUT_SECONDS = 120
MTIME_TOLERANCE_SECONDS = 2.0
TOTAL_CLI_STAGES = 7
_AUTO_TRIGGER_THRESHOLD = 120
```

### Project Structure — New Files

```
src/pipeline/application/cli/
├── __init__.py              (exists from 21.1)
├── protocols.py             (exists from 21.1)
├── context.py               (exists from 21.1)
├── invoker.py               (exists from 21.1)
├── history.py               (exists from 21.1)
├── commands/
│   ├── __init__.py          (NEW)
│   ├── validate_args.py     (NEW — ValidateArgsCommand)
│   ├── setup_workspace.py   (NEW — SetupWorkspaceCommand)
│   ├── download_cutaways.py (NEW — DownloadCutawaysCommand)
│   ├── run_elicitation.py   (NEW — RunElicitationCommand)
│   ├── run_stage.py         (NEW — RunStageCommand)
│   └── run_pipeline.py      (NEW — RunPipelineCommand)
└── hooks/
    ├── __init__.py          (NEW)
    ├── veo3_fire_hook.py    (NEW — Veo3FireHook)
    ├── veo3_await_hook.py   (NEW — Veo3AwaitHook)
    ├── manifest_hook.py     (NEW — ManifestBuildHook)
    └── encoding_hook.py     (NEW — EncodingPlanHook)

tests/unit/application/cli/
├── __init__.py              (exists from 21.1)
├── test_invoker.py          (exists from 21.1)
├── test_history.py          (exists from 21.1)
├── test_context.py          (exists from 21.1)
├── commands/
│   ├── __init__.py          (NEW)
│   ├── test_validate_args.py     (NEW)
│   ├── test_setup_workspace.py   (NEW)
│   ├── test_download_cutaways.py (NEW)
│   ├── test_run_elicitation.py   (NEW)
│   ├── test_run_stage.py         (NEW)
│   └── test_run_pipeline.py      (NEW)
└── hooks/
    ├── __init__.py          (NEW)
    ├── test_veo3_fire_hook.py    (NEW)
    ├── test_veo3_await_hook.py   (NEW)
    ├── test_manifest_hook.py     (NEW)
    └── test_encoding_hook.py     (NEW)

scripts/run_cli.py           (REWRITE — thin composition root)
```

### Files to Remove After Migration

```
tests/unit/scripts/test_run_cli.py              (89 tests → migrated)
tests/unit/scripts/test_cli_cutaway.py           (31 tests → migrated)
tests/unit/scripts/test_run_cli_atomic_write.py  (2 tests → migrated)
```

### References

- [Source: scripts/run_cli.py] — Full 1053-line file to decompose
- [Source: src/pipeline/application/cli/protocols.py] — Command, StageHook, InputReader, ClipDurationProber protocols (Story 21.1)
- [Source: src/pipeline/application/cli/context.py] — PipelineContext dataclass (Story 21.1)
- [Source: src/pipeline/application/cli/invoker.py] — PipelineInvoker (Story 21.1)
- [Source: src/pipeline/application/cli/history.py] — CommandHistory (Story 21.1)
- [Source: src/pipeline/infrastructure/adapters/ffprobe_adapter.py] — FfprobeAdapter (Story 21.1)
- [Source: src/pipeline/infrastructure/adapters/stdin_reader.py] — StdinReader (Story 21.1)
- [Source: src/pipeline/application/stage_runner.py] — StageRunner constructor injection
- [Source: src/pipeline/application/event_bus.py] — EventBus pattern
- [Source: src/pipeline/app/settings.py] — PipelineSettings fields
- [Source: src/pipeline/app/bootstrap.py] — DI wiring pattern
- [Source: src/pipeline/domain/ports.py] — ExternalClipDownloaderPort
- [Source: src/pipeline/application/manifest_builder.py] — ManifestBuilder for cutaway manifest
- [Source: src/pipeline/application/veo3_orchestrator.py] — Veo3Orchestrator
- [Source: src/pipeline/application/veo3_await_gate.py] — run_veo3_await_gate
- [Source: tests/unit/scripts/test_run_cli.py] — 89 existing tests to migrate
- [Source: tests/unit/scripts/test_cli_cutaway.py] — 31 existing tests to migrate
- [Source: tests/unit/scripts/test_run_cli_atomic_write.py] — 2 existing tests to migrate

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
