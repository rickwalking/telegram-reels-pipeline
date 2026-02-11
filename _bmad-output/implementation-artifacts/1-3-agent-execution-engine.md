# Story 1.3: Agent Execution Engine

Status: done

## Story

As a developer,
I want the orchestrator to execute BMAD agents via Claude Code CLI as subprocess calls,
So that pipeline stages can run AI agents and collect their output artifacts.

## Acceptance Criteria

1. **Given** a stage step file and agent definition, **When** the CliBackend executes `claude -p "{prompt}"`, **Then** the subprocess runs with the constructed prompt (step file + agent def + prior artifacts + elicitation context), **And** execution is bounded by `asyncio.timeout()`.

2. **Given** the agent process completes, **When** the orchestrator collects results, **Then** output artifacts are read from the per-run workspace directory, **And** an AgentResult is returned with status, artifacts, and session_id.

3. **Given** the agent process fails or times out, **When** the executor detects the failure, **Then** an AgentExecutionError is raised with the cause preserved (`raise ... from exc`).

## Tasks / Subtasks

- [x] **Task 1: Create PromptBuilder helper** (AC: #1)
  - [ ] Create `src/pipeline/application/prompt_builder.py`
  - [ ] `build_agent_prompt(request: AgentRequest) -> str` — constructs the full prompt string from step file + agent def + prior artifacts + elicitation context + attempt history
  - [ ] Read step file and agent definition file contents via `Path.read_text()`
  - [ ] Append prior artifacts as file path references (not inline content)
  - [ ] Append elicitation context as key-value section
  - [ ] Append attempt history (QA feedback from prior rework cycles) if present
  - [ ] Pure function — no I/O beyond reading the input files, no third-party imports
  - [ ] Application layer: imports domain only

- [x] **Task 2: Create CliBackend adapter** (AC: #1, #2, #3)
  - [ ] Create `src/pipeline/infrastructure/adapters/claude_cli_backend.py`
  - [ ] Implements `AgentExecutionPort` protocol (async)
  - [ ] `async execute(self, request: AgentRequest) -> AgentResult`
  - [ ] Constructor takes `timeout_seconds: float` (default from architecture: configurable) and `work_dir: Path` (per-run workspace directory)
  - [ ] Build prompt via `build_agent_prompt(request)`
  - [ ] Execute `claude -p "{prompt}"` as async subprocess via `asyncio.create_subprocess_exec`
  - [ ] Wrap execution in `asyncio.timeout(self._timeout_seconds)`
  - [ ] Capture stdout/stderr from subprocess
  - [ ] On success (returncode 0): scan workspace for output artifacts, construct AgentResult
  - [ ] On failure (returncode != 0): raise `AgentExecutionError` with stderr, preserving cause
  - [ ] On timeout (`TimeoutError`): kill process, raise `AgentExecutionError` from timeout
  - [ ] Parse session_id from Claude CLI output if available (regex or structured output)
  - [ ] Use `SessionId` NewType for the session identifier

- [x] **Task 3: Create ArtifactCollector helper** (AC: #2)
  - [ ] Create `src/pipeline/infrastructure/adapters/artifact_collector.py`
  - [ ] `collect_artifacts(work_dir: Path, stage: PipelineStage) -> tuple[Path, ...]`
  - [ ] Scan `work_dir` for output files produced by the agent
  - [ ] Return tuple of artifact paths (immutable, matching domain conventions)
  - [ ] Filter by expected file patterns for the given stage (e.g., `.md`, `.json`)
  - [ ] Infrastructure layer: can use pathlib, no third-party needed

- [x] **Task 4: Write PromptBuilder unit tests**
  - [ ] Create `tests/unit/application/test_prompt_builder.py`
  - [ ] Test prompt includes step file content
  - [ ] Test prompt includes agent definition content
  - [ ] Test prompt includes prior artifact paths
  - [ ] Test prompt includes elicitation context key-values
  - [ ] Test prompt includes attempt history when present
  - [ ] Test prompt handles empty optional fields gracefully
  - [ ] Use `tmp_path` to create mock step/agent files

- [x] **Task 5: Write CliBackend unit tests with mocked subprocess** (AC: #1, #2, #3)
  - [ ] Create `tests/unit/infrastructure/test_claude_cli_backend.py`
  - [ ] Mock `asyncio.create_subprocess_exec` to simulate CLI behavior
  - [ ] Test successful execution returns AgentResult with correct fields
  - [ ] Test non-zero exit code raises AgentExecutionError
  - [ ] Test timeout raises AgentExecutionError with timeout cause
  - [ ] Test AgentExecutionError preserves cause via `__cause__`
  - [ ] Test prompt is passed correctly to subprocess
  - [ ] Test session_id extraction from output (when present and absent)

- [x] **Task 6: Write ArtifactCollector unit tests**
  - [ ] Create `tests/unit/infrastructure/test_artifact_collector.py`
  - [ ] Test collects files from workspace directory
  - [ ] Test returns empty tuple for empty directory
  - [ ] Test filters by expected patterns
  - [ ] Use `tmp_path` for filesystem isolation

- [x] **Task 7: Run full validation suite**
  - [ ] `poetry run pytest tests/ -v --tb=short` — all tests pass, 80%+ coverage
  - [ ] `poetry run mypy` — zero errors (no path arg, uses pyproject.toml config)
  - [ ] `poetry run black --check src/ tests/`
  - [ ] `poetry run isort --check-only src/ tests/`
  - [ ] `poetry run ruff check src/ tests/`

## Dev Notes

### Architecture Compliance (CRITICAL)

**Application Layer Rules** (`src/pipeline/application/`):
- Imports from `domain/` ONLY — no third-party, no infrastructure
- `prompt_builder.py`: imports `domain.models` (AgentRequest), stdlib only
- Pure function: reads file contents from `Path` objects already in AgentRequest
- No I/O beyond `Path.read_text()` on paths provided in the request

**Infrastructure Layer Rules** (`src/pipeline/infrastructure/adapters/`):
- Imports from `domain/` and `application/` — plus stdlib `asyncio`, `subprocess`
- `claude_cli_backend.py` implements `AgentExecutionPort` protocol from `domain.ports`
- `artifact_collector.py` is a helper module — scans workspace for output files
- Can import `prompt_builder` from application layer

### Existing Domain Types (from Story 1.1 — DO NOT RECREATE)

```python
# domain/types.py — NewType aliases
RunId = NewType("RunId", str)
AgentId = NewType("AgentId", str)
SessionId = NewType("SessionId", str)
GateName = NewType("GateName", str)

# domain/enums.py
PipelineStage  # ROUTER, RESEARCH, ..., COMPLETED, FAILED

# domain/models.py — frozen dataclasses
@dataclass(frozen=True)
class AgentRequest:
    stage: PipelineStage
    step_file: Path
    agent_definition: Path
    prior_artifacts: tuple[Path, ...] = field(default_factory=tuple)
    elicitation_context: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    attempt_history: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class AgentResult:
    status: str
    artifacts: tuple[Path, ...] = field(default_factory=tuple)
    session_id: SessionId = SessionId("")
    duration_seconds: float = 0.0
    # __post_init__: duration_seconds must be non-negative

# domain/errors.py
class AgentExecutionError(PipelineError):
    """Agent subprocess failure, timeout, or unexpected exit."""
    # Usage: raise AgentExecutionError("msg") from exc

# domain/ports.py — AgentExecutionPort protocol
@runtime_checkable
class AgentExecutionPort(Protocol):
    async def execute(self, request: AgentRequest) -> AgentResult: ...
```

### Claude Code CLI Invocation Pattern

From architecture.md — Phase 1 uses CLI subprocess:

```bash
claude -p "{prompt}"
```

Key details:
- `claude` binary must be on PATH (available in Docker container)
- `-p` flag sends the prompt as a single argument
- Claude Code writes output to the current working directory or specified paths
- Process stdout contains agent response text
- Process stderr contains error/diagnostic output
- Session ID may be extractable from output (check `--output-format json` flag)
- Exit code 0 = success, non-zero = failure

### Subprocess Execution Pattern

```python
import asyncio

async def _run_cli(prompt: str, work_dir: Path, timeout: float) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(work_dir),
    )
    async with asyncio.timeout(timeout):
        stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode or 0
```

### Agent Prompt Contract (from architecture.md)

Standardized input bundle per agent:
- `stage_requirements` — what this stage must produce (from step file)
- `prior_artifacts` — outputs from completed stages (file paths, not inline)
- `elicitation_context` — user preferences from Router Agent
- `attempt_history` — prior attempts and QA feedback (for rework cycles)

### Error Handling Pattern

```python
# On subprocess failure:
raise AgentExecutionError(f"Agent {request.stage.value} failed: {stderr}") from exc

# On timeout:
raise AgentExecutionError(f"Agent {request.stage.value} timed out after {timeout}s") from exc

# NEVER catch-and-silence: except Exception: pass is BANNED
# Recovery chain (Story 1.7) handles all errors — components don't retry independently
```

### Async Boundaries (from architecture.md)

- `async` for: agent calls, subprocess execution
- `asyncio.timeout()` for all bounded operations
- Synchronous for: prompt building (pure transforms)

### Testing Patterns

- **PromptBuilder tests**: Pure unit tests, create temp step/agent files, verify prompt structure
- **CliBackend tests**: Mock `asyncio.create_subprocess_exec` to avoid real subprocess calls
  - Use `unittest.mock.AsyncMock` for the subprocess
  - Simulate stdout/stderr/returncode
  - Test success, failure, and timeout paths
- **ArtifactCollector tests**: Use `tmp_path` for real filesystem, create mock output files
- **All tests**: Use existing domain fixtures from `conftest.py`
- **Async tests**: `pytest-asyncio` with `asyncio_mode = "auto"` — just mark tests `async def`

### Mocking asyncio.create_subprocess_exec

```python
from unittest.mock import AsyncMock, patch, MagicMock

@patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
async def test_successful_execution(mock_create_subprocess):
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b"output text", b"")
    mock_proc.returncode = 0
    mock_create_subprocess.return_value = mock_proc

    # ... test CliBackend.execute()
```

### Phase 2 Note (NOT IN SCOPE)

Phase 2 will add `SdkBackend` using the Claude Agent SDK `query()` API. The `AgentExecutionPort` protocol is designed to support both backends. Story 1.3 implements ONLY the CLI backend. Do NOT create `claude_sdk_backend.py`.

### Project Environment Notes (from Stories 1.1 + 1.2)

- Python 3.13.5 in Docker container (targeting >=3.11)
- Poetry 2.3.2 at `/home/umbrel/.local/bin/poetry`
- Run mypy WITHOUT path arg: `poetry run mypy` (uses pyproject.toml `packages = ["pipeline"]`)
- Run tests: `poetry run pytest tests/ -v --tb=short`
- src layout: `[[tool.poetry.packages]]` with `include = "pipeline"`, `from = "src"`
- Frozen dataclasses with `tuple` (not list), `Mapping` + `MappingProxyType` (not dict)
- `raise X from Y` pattern for exception chaining (not manual `__cause__`)
- type stubs: `types-PyYAML`, `types-aiofiles` already in dev deps
- Review finding L1 (deferred): events are bare strings — may become an enum in future

### Previous Story Learnings (from Stories 1.1 + 1.2)

- **Poetry bootstrap**: Use `/home/umbrel/.local/bin/poetry` (not system `poetry`)
- **mypy path**: Run `poetry run mypy` without path arg — uses pyproject.toml `packages`
- **ruff auto-fix**: `poetry run ruff check --fix src/ tests/` for simple fixes
- **Frozen dataclass mutation**: Use `dataclasses.replace()` for new instances, `object.__setattr__` for `__post_init__`
- **Error resilience**: Wrap deserialization in try/except, don't let one corrupt file abort batch operations
- **Protocol compliance**: Use `TYPE_CHECKING` guard to verify adapter matches port protocol
- **Atomic writes**: write-to-tmp + rename pattern for all state file mutations
- **Test directory structure**: `tests/unit/application/`, `tests/unit/infrastructure/`, `tests/integration/`

### References

- [Source: architecture.md#Critical Decisions] — Claude Code CLI for Phase 1 agent execution
- [Source: architecture.md#Communication Patterns] — Agent-to-agent via orchestrator, artifacts via filesystem
- [Source: architecture.md#Phase Boundaries] — CLI Phase 1 vs SDK Phase 2
- [Source: architecture.md#Process Patterns] — Async boundaries, error propagation, checkpoint timing
- [Source: architecture.md#Port Boundaries] — AgentExecutionPort → CliBackend adapter
- [Source: architecture.md#Data Flow] — Orchestrator spawns CLI with step file as prompt
- [Source: architecture.md#Agent Prompt Contracts] — Standardized input bundle per agent
- [Source: architecture.md#Project Structure] — claude_cli_backend.py in infrastructure/adapters/
- [Source: epics.md#Story 1.3] — Original acceptance criteria
- [Source: 1-2-pipeline-state-machine-file-persistence.md] — Previous story learnings, review findings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- 3 timeout tests initially failed due to `AsyncMock(side_effect=asyncio.sleep(10))` — `side_effect` must be a callable, not a coroutine object. Fixed with `_slow_communicate()` helper returning AsyncMock with async function as side_effect.
- ruff F541: f-string without placeholders in `prompt_builder.py:40` — removed `f` prefix.
- mypy: 2 unused `# type: ignore[possibly-undefined]` on `proc.kill()`/`proc.wait()` — mypy correctly determined `proc` is always defined before the TimeoutError catch. Removed.
- black reformatted `claude_cli_backend.py` (long line in error message).

### Completion Notes List

- All 7 tasks complete. 169 tests passing, 97.64% coverage.
- black, ruff, isort, mypy: all clean.
- PromptBuilder is a pure application-layer function (domain imports only).
- CliBackend satisfies AgentExecutionPort protocol (TYPE_CHECKING guard + runtime isinstance test).
- ArtifactCollector scans workspace for .md/.json/.txt/.yaml/.yml files.
- 3 RuntimeWarnings in timeout tests (unawaited coroutine on `proc.kill()`) are expected — real `Process.kill()` is sync, but AsyncMock makes it async. Does not affect correctness.

### File List

- `src/pipeline/application/prompt_builder.py` — NEW — PromptBuilder helper (Task 1)
- `src/pipeline/infrastructure/adapters/claude_cli_backend.py` — NEW — CliBackend adapter (Task 2)
- `src/pipeline/infrastructure/adapters/artifact_collector.py` — NEW — ArtifactCollector helper (Task 3)
- `tests/unit/application/test_prompt_builder.py` — NEW — 10 PromptBuilder unit tests (Task 4)
- `tests/unit/infrastructure/test_claude_cli_backend.py` — NEW — 21 CliBackend unit tests (Task 5)
- `tests/unit/infrastructure/test_artifact_collector.py` — NEW — 10 ArtifactCollector unit tests (Task 6)
- `tests/unit/infrastructure/__init__.py` — NEW — package init for test discovery

## Senior Developer Review (AI)

### Review Date: 2026-02-10

### Reviewer: Claude Opus 4.6 + Gemini 2.5 Pro (external expert)

### Issues Found: 2 HIGH, 5 MEDIUM, 3 LOW

### Issues Fixed (7 of 7 HIGH+MEDIUM):

1. **[H1] FileNotFoundError from prompt_builder propagates unwrapped** `cli_backend.py:47`
   - Moved `build_agent_prompt()` inside the try block; added `except FileNotFoundError` handler wrapping in AgentExecutionError
   - Also reordered except clauses: FileNotFoundError (more specific) before OSError (parent class)

2. **[H2] UnicodeDecodeError not handled on stdout/stderr decode** `cli_backend.py:72`
   - Changed `.decode()` to `.decode(errors="replace")` on both stdout and stderr

3. **[M1] Dead code — unused `duration` in error handlers** `cli_backend.py:65,68`
   - Removed unused `duration = time.monotonic() - start` from both TimeoutError and OSError handlers

4. **[M2] Unused `stage` parameter in `collect_artifacts()`** `artifact_collector.py:13`
   - Removed `stage: PipelineStage` parameter from signature; removed `PipelineStage` import
   - Updated call site in `cli_backend.py:79` and all 10 test calls
   - Added "Only scans top-level files (not recursive)" to docstring (also addresses L2)

5. **[M3] `proc.returncode or 0` masks None** `cli_backend.py:74`
   - Changed to `proc.returncode if proc.returncode is not None else 0`

6. **[M4] No test for missing step_file FileNotFoundError** `test_claude_cli_backend.py`
   - Added `test_missing_step_file_raises_agent_execution_error` and `test_missing_step_file_preserves_cause`

7. **[M5] No runtime isinstance test for CliBackend protocol** `test_claude_cli_backend.py`
   - Added `TestCliBackendProtocol::test_satisfies_agent_execution_port`

### Issues Deferred (3 LOW):

- **[L1] Timeout tests duplicate mock setup** — Extracted to `_make_slow_proc()` shared helper (partially addressed)
- **[L2] artifact_collector top-level only undocumented** — Addressed in M2 fix (added docstring note)
- **[L3] `_extract_session_id` fragile string parsing** — Known limitation; will be revisited when CLI output format is finalized

### Post-Review Validation

- 169 tests passing, 97.64% coverage
- black, ruff, isort, mypy: all clean
