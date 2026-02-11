# Story 1.1: Project Scaffolding & Domain Model

Status: done

## Story

As a developer,
I want the project scaffolded with Poetry, Hexagonal Architecture, and all domain types defined,
So that I have a solid foundation with enforced layer boundaries to build pipeline components on.

## Acceptance Criteria

1. **Given** a fresh project directory, **When** I run `poetry install`, **Then** all dependencies are installed and the virtual environment is active, **And** `pyproject.toml` contains tool config for black, isort, ruff, mypy, pytest.

2. **Given** the project structure exists, **When** I inspect `src/pipeline/domain/`, **Then**:
   - `types.py` defines `NewType` for `RunId`, `AgentId`, `SessionId`, `GateName`
   - `enums.py` defines `PipelineStage`, `QADecision`, `EscalationState`, `RevisionType`
   - `models.py` defines frozen dataclasses: `AgentRequest`, `AgentResult`, `QACritique`, `CropRegion`, `VideoMetadata`, `QueueItem`, `RunState`, `PipelineEvent`
   - `errors.py` defines `PipelineError` hierarchy: `ConfigurationError`, `ValidationError`, `AgentExecutionError`, `UnknownLayoutError`
   - `ports.py` defines 8 Port Protocols: `AgentExecutionPort`, `ModelDispatchPort`, `MessagingPort`, `VideoProcessingPort`, `VideoDownloadPort`, `StateStorePort`, `FileDeliveryPort`, `KnowledgeBasePort`
   - `transitions.py` defines the FSM transition table and guard definitions as pure data

3. **Given** the domain layer, **When** I run `mypy --strict src/pipeline/domain/`, **Then** zero type errors and `domain/` imports only from stdlib.

## Tasks / Subtasks

- [x] **Task 1: Initialize Poetry project** (AC: #1)
  - [x] Run `poetry init --name telegram-reels-pipeline --python "^3.11"`
  - [x] Add runtime deps: `poetry add pydantic pyyaml python-telegram-bot aiofiles`
  - [x] Add dev deps: `poetry add --group dev black isort ruff mypy pytest pytest-asyncio pytest-cov`
  - [x] Verify `poetry install` succeeds and venv is active

- [x] **Task 2: Configure tooling in pyproject.toml** (AC: #1)
  - [x] black: `line-length = 120`
  - [x] isort: `profile = "black"`, `line_length = 120`
  - [x] ruff: `target-version = "py311"`, enable `C901`
  - [x] mypy: `strict = true`, `disallow_any_generics = true`
  - [x] pytest: `asyncio_mode = "auto"`, configure `pytest-cov` with 80% minimum
  - [x] Add `.editorconfig` with consistent indent/encoding settings

- [x] **Task 3: Create complete directory structure** (AC: #2)
  - [x] Create Hexagonal layers: `src/pipeline/{domain,application,infrastructure/adapters,app}/`
  - [x] Create infrastructure sub-packages: `infrastructure/{listeners,telegram_bot}/`
  - [x] Create test structure: `tests/{unit/{domain,application},integration}/`
  - [x] Create runtime dirs: `config/`, `systemd/`, `workspace/{runs,queue/{inbox,processing,completed},knowledge}/`
  - [x] Create script dir: `scripts/`
  - [x] Create BMAD dirs: `workflows/{stages,revision-flows,qa/gate-criteria}/`, `agents/{router,research,transcript,content-creator,layout-detective,ffmpeg-engineer,qa,delivery}/`
  - [x] Add `__init__.py` to all Python packages
  - [x] Add `.gitignore` (workspace/, .env, __pycache__, .mypy_cache/, dist/, *.egg-info/)
  - [x] Add `.env.example` with keys: `TELEGRAM_TOKEN`, `CHAT_ID`, `ANTHROPIC_API_KEY`

- [x] **Task 4: Define domain types** (AC: #2)
  - [x] `types.py`: `RunId = NewType("RunId", str)`, `AgentId = NewType("AgentId", str)`, `SessionId = NewType("SessionId", str)`, `GateName = NewType("GateName", str)`

- [x] **Task 5: Define domain enums** (AC: #2)
  - [x] `PipelineStage`: `ROUTER`, `RESEARCH`, `TRANSCRIPT`, `CONTENT`, `LAYOUT_DETECTIVE`, `FFMPEG_ENGINEER`, `ASSEMBLY`, `DELIVERY`, `COMPLETED`, `FAILED`
  - [x] `QADecision`: `PASS`, `REWORK`, `FAIL`
  - [x] `EscalationState`: `NONE`, `LAYOUT_UNKNOWN`, `QA_EXHAUSTED`, `ERROR_ESCALATED`
  - [x] `RevisionType`: `EXTEND_MOMENT`, `FIX_FRAMING`, `DIFFERENT_MOMENT`, `ADD_CONTEXT`

- [x] **Task 6: Define domain models** (AC: #2)
  - [x] `AgentRequest`: frozen dataclass with `stage`, `step_file`, `agent_definition`, `prior_artifacts`, `elicitation_context`, `attempt_history`
  - [x] `AgentResult`: frozen dataclass with `status`, `artifacts` (list of paths), `session_id`, `duration_seconds`
  - [x] `QACritique`: frozen dataclass with `decision`, `score`, `gate`, `attempt`, `blockers`, `prescriptive_fixes`, `confidence`
  - [x] `CropRegion`: frozen dataclass with `x`, `y`, `width`, `height`, `layout_name`
  - [x] `VideoMetadata`: frozen dataclass with `title`, `duration_seconds`, `channel`, `publish_date`, `description`, `url`
  - [x] `QueueItem`: frozen dataclass with `url`, `telegram_update_id`, `queued_at`, `topic_focus` (optional)
  - [x] `RunState`: frozen dataclass with `run_id`, `youtube_url`, `current_stage`, `current_attempt`, `qa_status`, `stages_completed`, `escalation_state`, `best_of_three_overrides`, `created_at`, `updated_at`
  - [x] `PipelineEvent`: frozen dataclass with `timestamp`, `event_name`, `stage`, `data`
  - [x] Use stdlib `dataclasses.dataclass(frozen=True)` — NOT Pydantic (domain = stdlib only)

- [x] **Task 7: Define domain errors** (AC: #2)
  - [x] `PipelineError(Exception)`: base class with `message` and optional `cause`
  - [x] `ConfigurationError(PipelineError)`: invalid config, missing env vars
  - [x] `ValidationError(PipelineError)`: schema/input validation failure
  - [x] `AgentExecutionError(PipelineError)`: agent subprocess failure, timeout
  - [x] `UnknownLayoutError(PipelineError)`: unrecognized camera layout needing escalation

- [x] **Task 8: Define 8 Port Protocols** (AC: #2)
  - [x] `AgentExecutionPort`: `async execute(request: AgentRequest) -> AgentResult`
  - [x] `ModelDispatchPort`: `async dispatch(role: str, prompt: str, model: str | None) -> str`
  - [x] `MessagingPort`: `async ask_user(question: str) -> str`, `async notify_user(message: str) -> None`, `async send_file(path: Path, caption: str) -> None`
  - [x] `VideoProcessingPort`: `async extract_frames(video: Path, timestamps: list[float]) -> list[Path]`, `async crop_and_encode(video: Path, segments: list[CropRegion], output: Path) -> Path`
  - [x] `VideoDownloadPort`: `async download_metadata(url: str) -> VideoMetadata`, `async download_subtitles(url: str, output: Path) -> Path`, `async download_video(url: str, output: Path) -> Path`
  - [x] `StateStorePort`: `async save_state(state: RunState) -> None`, `async load_state(run_id: RunId) -> RunState | None`, `async list_incomplete_runs() -> list[RunState]`
  - [x] `FileDeliveryPort`: `async upload(path: Path) -> str` (returns URL)
  - [x] `KnowledgeBasePort`: `async get_strategy(layout_name: str) -> CropRegion | None`, `async save_strategy(layout_name: str, region: CropRegion) -> None`, `async list_strategies() -> dict[str, CropRegion]`
  - [x] All ports use `typing.Protocol` with `typing.runtime_checkable` decorator

- [x] **Task 9: Define FSM transition table** (AC: #2)
  - [x] `transitions.py`: transition table as `dict[tuple[PipelineStage, str], PipelineStage]` mapping `(current_stage, event) -> next_stage`
  - [x] Events: `qa_pass`, `qa_rework`, `qa_fail`, `stage_complete`, `escalation_requested`, `escalation_resolved`
  - [x] Guard definitions as `dict[str, Callable]` — pure functions returning bool
  - [x] All data, no I/O — stdlib only

- [x] **Task 10: Create initial config files** (AC: #1)
  - [x] `config/pipeline.yaml`: placeholder structure with timeframes, thresholds, model routing
  - [x] `config/crop-strategies.yaml`: empty knowledge base with schema comment
  - [x] `config/quality-gates.yaml`: placeholder structure for per-gate criteria

- [x] **Task 11: Write domain unit tests** (AC: #3)
  - [x] `tests/unit/domain/test_models.py`: frozen dataclass construction, immutability verification
  - [x] `tests/unit/domain/test_enums.py`: enum member coverage, stage ordering validation
  - [x] `tests/unit/domain/test_transitions.py`: transition table completeness, all stages reachable, guard logic
  - [x] `tests/conftest.py`: shared fixtures (sample RunState factory, sample QACritique factory)

- [x] **Task 12: Validate domain purity** (AC: #3)
  - [x] Run `mypy --strict src/pipeline/domain/` — zero errors
  - [x] Verify no imports from `application/`, `infrastructure/`, `app/`, or third-party
  - [x] Run `black --check`, `isort --check`, `ruff check` — zero violations
  - [x] Run `pytest tests/unit/domain/` — all pass

## Dev Notes

### Architecture Compliance (CRITICAL)

**Hexagonal Architecture — Domain Layer Rules:**
- Domain layer (`src/pipeline/domain/`) imports ONLY from Python stdlib
- NO Pydantic, NO PyYAML, NO third-party in domain — use `dataclasses`, `enum`, `typing`, `pathlib`, `datetime`
- All domain models are `@dataclass(frozen=True)` — immutable value objects
- Ports use `typing.Protocol` (stdlib since Python 3.8) with `@runtime_checkable`
- Transitions table is pure data — dict literals, no I/O, no side effects

**Import Rules by Layer:**

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| `domain/` | stdlib only | application, infrastructure, app, third-party |
| `application/` | domain | infrastructure, app |
| `infrastructure/` | domain, application, third-party | app |
| `app/` | all layers | — |

### Naming Conventions

- Variables/functions: `snake_case` — `pipeline_state`, `calculate_crop_region`
- Classes: `PascalCase` — `PipelineOrchestrator`, `QAReflectionLoop`
- Constants: `UPPER_SNAKE_CASE` — `MAX_QA_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS`
- Enums: `PascalCase` class, `UPPER_CASE` members — `PipelineStage.QA_CONTENT`
- Modules: `snake_case.py` — `state_machine.py`, `model_router.py`
- Config files: `kebab-case.yaml` — `crop-strategies.yaml`, `quality-gates.yaml`
- Full words over abbreviations: `context` not `ctx`, `repository` not `repo`
- Universal acronyms allowed: `llm`, `mcp`, `qa`, `api`, `url`

### Frontmatter Schema (run.md) — Exact Fields Required

```yaml
---
run_id: "<timestamp>-<short_id>"
youtube_url: "<url>"
current_stage: "<PipelineStage enum value in snake_case>"
current_attempt: <int>
qa_status: "pending | passed | rework | failed"
stages_completed: [<list of snake_case stage names>]
escalation_state: "none | layout_unknown | qa_exhausted | error_escalated"
best_of_three_overrides: [<list of gate names>]
created_at: "<ISO 8601>"
updated_at: "<ISO 8601>"
---
```

The `RunState` dataclass MUST map 1:1 to these frontmatter fields.

### QA Critique Schema (Pydantic-validated at runtime, but domain model is stdlib dataclass)

```json
{
  "decision": "PASS | REWORK | FAIL",
  "score": 85,
  "gate": "<snake_case gate name>",
  "attempt": 2,
  "blockers": [{"severity": "critical|high|medium|low", "description": "..."}],
  "prescriptive_fixes": ["exact fix instruction 1"],
  "confidence": 0.92
}
```

The `QACritique` domain model should have fields matching this schema. Pydantic validation happens in the infrastructure layer (adapters), not in domain.

### Error Handling Patterns

- Domain errors: raise specific `PipelineError` subclass
- Never catch-and-silence: `except Exception: pass` is BANNED
- Always preserve cause: `raise ... from exc`
- Error hierarchy allows callers to catch at appropriate granularity

### Testing Standards

- Framework: pytest + pytest-asyncio + pytest-cov
- Pattern: AAA (Arrange-Act-Assert)
- Naming: `test_<unit>_<scenario>_<expected>` — e.g., `test_fsm_qa_pass_transitions_to_next_stage`
- Domain tests: pure function tests, no I/O mocks needed
- Use fakes over mocks for domain collaborators
- Minimum 80% coverage target
- Property tests for pure transforms where applicable

### Project Structure Notes

Full project directory structure is defined in architecture.md. This story creates the skeleton — only domain layer files have content. Application, infrastructure, and app layer files are created as empty `__init__.py` placeholders. BMAD workflow directories and config directories are created as empty structure.

The project root is `telegram-reels-pipeline/` and should be created as a subdirectory of the working directory.

### Package Versions (as of February 2026)

```
# Runtime
pydantic = "^2.12"
pyyaml = "^6.0"
python-telegram-bot = "^22.6"
aiofiles = "^25.1"

# Dev
black = "^26.1"
isort = "^7.0"
ruff = "^0.15"
mypy = "^1.19"
pytest = "^9.0"
pytest-asyncio = "^1.3"
pytest-cov = "^7.0"
```

All confirmed compatible with Python 3.11+ on ARM aarch64 (Raspberry Pi).

### References

- [Source: architecture.md#Starter Template Evaluation] — Poetry init commands, scaffolding approach
- [Source: architecture.md#Core Architectural Decisions] — Hexagonal layers, 8 Port Protocols, FSM design
- [Source: architecture.md#Implementation Patterns] — Naming conventions, structure patterns, format patterns
- [Source: architecture.md#Project Structure & Boundaries] — Complete directory tree, layer rules
- [Source: architecture.md#Decision Impact Analysis] — Step 1: Domain types, entities, Port Protocols (zero external deps)
- [Source: epics.md#Story 1.1] — Original acceptance criteria
- [Source: prd.md#Functional Requirements] — FR20-FR24, FR35, FR38-FR40 (Epic 1 FRs)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Poetry 2.3.2 installed via pipx (not pre-installed in Docker container)
- `requires-python` changed from `^3.11` to `>=3.11` for ruff TOML parser compatibility
- `py.typed` PEP 561 marker added for mypy installed-package import analysis
- `mypy_path = "src"` and `packages = ["pipeline"]` added to pyproject.toml for src layout

### Completion Notes List

- All 12 tasks and all subtasks completed
- Poetry project initialized with 4 runtime + 7 dev deps
- Complete Hexagonal Architecture directory structure created
- 6 domain modules: types, enums, models, errors, ports, transitions
- All domain models are frozen stdlib dataclasses (no Pydantic in domain)
- 8 Port Protocols defined with @runtime_checkable
- FSM transition table: 8 stages, qa_pass/qa_rework/qa_fail/escalation events
- 66 unit tests, 100% domain coverage
- All linters pass: black, isort, ruff, mypy --strict
- 3 config YAML placeholders created

### File List

telegram-reels-pipeline/pyproject.toml
telegram-reels-pipeline/poetry.lock
telegram-reels-pipeline/.editorconfig
telegram-reels-pipeline/.gitignore
telegram-reels-pipeline/.env.example
telegram-reels-pipeline/src/pipeline/py.typed
telegram-reels-pipeline/src/pipeline/__init__.py
telegram-reels-pipeline/src/pipeline/domain/__init__.py
telegram-reels-pipeline/src/pipeline/domain/types.py
telegram-reels-pipeline/src/pipeline/domain/enums.py
telegram-reels-pipeline/src/pipeline/domain/models.py
telegram-reels-pipeline/src/pipeline/domain/errors.py
telegram-reels-pipeline/src/pipeline/domain/ports.py
telegram-reels-pipeline/src/pipeline/domain/transitions.py
telegram-reels-pipeline/src/pipeline/application/__init__.py
telegram-reels-pipeline/src/pipeline/infrastructure/__init__.py
telegram-reels-pipeline/src/pipeline/infrastructure/adapters/__init__.py
telegram-reels-pipeline/src/pipeline/infrastructure/listeners/__init__.py
telegram-reels-pipeline/src/pipeline/infrastructure/telegram_bot/__init__.py
telegram-reels-pipeline/src/pipeline/app/__init__.py
telegram-reels-pipeline/tests/__init__.py
telegram-reels-pipeline/tests/conftest.py
telegram-reels-pipeline/tests/unit/__init__.py
telegram-reels-pipeline/tests/unit/domain/__init__.py
telegram-reels-pipeline/tests/unit/domain/test_models.py
telegram-reels-pipeline/tests/unit/domain/test_enums.py
telegram-reels-pipeline/tests/unit/domain/test_transitions.py
telegram-reels-pipeline/tests/unit/domain/test_errors.py
telegram-reels-pipeline/tests/unit/domain/test_ports.py
telegram-reels-pipeline/tests/unit/application/__init__.py
telegram-reels-pipeline/tests/integration/__init__.py
telegram-reels-pipeline/config/pipeline.yaml
telegram-reels-pipeline/config/crop-strategies.yaml
telegram-reels-pipeline/config/quality-gates.yaml
