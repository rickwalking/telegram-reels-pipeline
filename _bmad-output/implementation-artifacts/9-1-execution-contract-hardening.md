# Story 9.1: Execution Contract Hardening

Status: ready-for-dev

## Story

As a developer,
I want execution contracts hardened so that CliBackend uses per-run workspaces, ArtifactCollector includes video files, crash recovery actually resumes runs, and the Anthropic API key reaches Claude subprocesses,
So that the pipeline infrastructure works correctly when content files (Epics 7-8) are added.

## Acceptance Criteria

1. **Given** PipelineRunner calls CliBackend.execute() for a stage,
   **When** the agent subprocess runs,
   **Then** the working directory is the per-run workspace path (not the global `settings.workspace_dir`),
   **And** agent output artifacts land in the correct run directory.

2. **Given** an agent produces `.mp4` video files during the ASSEMBLY stage,
   **When** ArtifactCollector scans the workspace,
   **Then** `.mp4` files are included in the collected artifacts tuple,
   **And** the DELIVERY stage receives them via `prior_artifacts`.

3. **Given** `ANTHROPIC_API_KEY` is set in the environment,
   **When** CliBackend spawns `claude -p "..."`,
   **Then** the subprocess inherits `ANTHROPIC_API_KEY` in its environment,
   **And** the Claude CLI can authenticate with the Anthropic API.

4. **Given** crash recovery finds interrupted runs on startup,
   **When** `scan_and_recover()` returns recovery plans,
   **Then** each plan is fed back into PipelineRunner to resume from the last completed stage,
   **And** the user is notified via Telegram that a run is being resumed.

5. **Given** the pipeline uses `RevisionRouter`, `RevisionHandler`, `LayoutEscalationHandler`, and `PipelineStateMachine`,
   **When** the orchestrator is bootstrapped,
   **Then** these components are instantiated and available on the Orchestrator dataclass,
   **And** they are wired with the correct port dependencies.

6. **Given** all contract fixes are applied,
   **When** I run the full test suite,
   **Then** all existing 628+ tests still pass with no regressions,
   **And** new tests cover each contract fix (min 80% coverage on changed files).

## Tasks / Subtasks

- [ ] Task 1: Fix CliBackend per-run workspace (AC: #1)
  - [ ] Modify `CliBackend.execute()` to accept a `workspace` parameter (Path) that overrides `self._work_dir`
  - [ ] Update `asyncio.create_subprocess_exec` call to set `cwd=workspace`
  - [ ] Update `StageRunner` to pass workspace path through to CliBackend
  - [ ] Add tests: verify subprocess `cwd` matches workspace, not global dir

- [ ] Task 2: Fix ArtifactCollector to include .mp4 (AC: #2)
  - [ ] In `artifact_collector.py`, add `.mp4` to collected extensions (alongside .json, .md, .txt, etc.)
  - [ ] Verify `_ARTIFACT_EXTENSIONS` or equivalent includes video outputs
  - [ ] Add test: workspace with .mp4 file is collected

- [ ] Task 3: Propagate ANTHROPIC_API_KEY to subprocess (AC: #3)
  - [ ] In `CliBackend.execute()`, ensure `env` parameter to subprocess includes `ANTHROPIC_API_KEY` from `os.environ`
  - [ ] If `env` is explicitly set, merge with parent environment
  - [ ] Add test: verify subprocess env includes API key

- [ ] Task 4: Persist workspace path in RunState for recovery (AC: #4)
  - [ ] Add `workspace_path: str = ""` field to `RunState` frozen dataclass in `domain/models.py`
  - [ ] Update `PipelineRunner.run()` to populate workspace_path when creating initial RunState
  - [ ] Update `FileStateStore` frontmatter schema to include workspace_path
  - [ ] Alternative: make `WorkspaceManager.create_workspace()` accept a `run_id` and use it as directory name (deterministic)
  - [ ] Add test: RunState round-trips workspace_path through FileStateStore

- [ ] Task 5: Wire crash recovery resume into pipeline (AC: #4)
  - [ ] In `main.py`, after `scan_and_recover()` returns plans, call `pipeline_runner.resume(plan, workspace)` for each
  - [ ] Add `PipelineRunner.resume(plan: RecoveryPlan, workspace: Path)` method that starts from `plan.resume_from` stage
  - [ ] Locate workspace from RunState.workspace_path (or reconstruct from run_id if deterministic)
  - [ ] Add test: recovery plan triggers pipeline resume from correct stage

- [ ] Task 6: Wire orphaned components into bootstrap (AC: #5)
  - [ ] Add `RevisionRouter` to Orchestrator dataclass
  - [ ] Add `RevisionHandler` to Orchestrator dataclass
  - [ ] Add `LayoutEscalationHandler` to Orchestrator dataclass
  - [ ] Add `PipelineStateMachine` to Orchestrator dataclass
  - [ ] Instantiate all in `create_orchestrator()` with correct port dependencies
  - [ ] Add tests: verify Orchestrator has all components after bootstrap

- [ ] Task 7: Run full test suite + coverage check (AC: #6)
  - [ ] `poetry run pytest tests/ -x -q` — all pass
  - [ ] `poetry run ruff check src/ tests/` — clean
  - [ ] `poetry run mypy` — clean
  - [ ] Verify min 80% coverage on changed files

## Dev Notes

### Critical Codex Audit Findings (source of this story)

These are bugs found by Codex 5.3 planner review that must be fixed before pipeline can run:

1. **CliBackend workspace isolation**: `CliBackend.__init__` takes a global `work_dir` (set to `settings.workspace_dir` in bootstrap). But `PipelineRunner.run()` creates per-run workspaces. Agent output needs to go to the per-run workspace, not the global one. Fix: add `workspace` override parameter to `execute()`.

2. **ArtifactCollector .mp4 exclusion**: Check `infrastructure/adapters/artifact_collector.py` for the file extension filter. The ASSEMBLY stage produces `.mp4` files that DELIVERY needs. If collector skips them, delivery fails silently.

3. **API key propagation**: `asyncio.create_subprocess_exec` with explicit `env=` replaces the parent env. Must either not pass `env` (inherits parent) or explicitly merge `os.environ` into any custom env dict.

4. **Orphaned components**: These classes exist with full implementations and tests but are never instantiated:
   - `RevisionRouter` in `application/revision_router.py`
   - `RevisionHandler` in `application/revision_handler.py`
   - `LayoutEscalationHandler` in `application/layout_escalation.py`
   - `PipelineStateMachine` in `application/state_machine.py`

5. **Crash recovery gap**: `CrashRecoveryHandler.scan_and_recover()` builds `RecoveryPlan` objects but nobody acts on them. `main.py` logs the count but doesn't resume.

6. **Workspace/Run identity split**: `WorkspaceManager.create_workspace()` generates `{timestamp}-{uuid6}` directory names independently from `PipelineRunner._generate_run_id()` which generates `{timestamp}-{microseconds}-{random4}`. RunState stores `run_id` but NOT the workspace path. On crash recovery, there's no way to locate the workspace for a given run_id. Fix: either persist `workspace_path` in RunState or make workspace names deterministic from run_id.

### Architecture Compliance

- Domain layer: NO changes needed (contracts are in application/infrastructure)
- Application layer: can import domain only
- Infrastructure layer: can import domain + application + third-party
- All new dataclass fields must follow frozen/immutable conventions
- Exception chaining: `raise X from Y` always
- Async for all I/O operations

### Existing File Locations

```
src/pipeline/infrastructure/adapters/claude_cli_backend.py  # CliBackend
src/pipeline/infrastructure/adapters/artifact_collector.py   # ArtifactCollector
src/pipeline/application/crash_recovery.py                   # CrashRecoveryHandler
src/pipeline/application/stage_runner.py                     # StageRunner
src/pipeline/application/revision_router.py                  # RevisionRouter
src/pipeline/application/revision_handler.py                 # RevisionHandler
src/pipeline/application/layout_escalation.py                # LayoutEscalationHandler
src/pipeline/application/state_machine.py                    # PipelineStateMachine
src/pipeline/app/bootstrap.py                                # Orchestrator + create_orchestrator()
src/pipeline/app/main.py                                     # Entry point
```

### Testing Standards

- AAA pattern (Arrange-Act-Assert)
- Fakes over mocks for domain collaborators
- `test_<unit>_<scenario>_<expected>` naming
- Async tests with pytest-asyncio
- Min 80% coverage on changed files

### References

- [Source: retrospective-epics-1-6.md#Critical Gap 4] — Pipeline never executes
- [Source: retrospective-epics-1-6.md#Critical Gap 1] — Agent definitions crash on read
- [Codex 5.3 Planner Review] — 7 additional gaps beyond retrospective
- [Source: architecture.md#Core Architectural Decisions] — Hexagonal layers, port protocols

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
