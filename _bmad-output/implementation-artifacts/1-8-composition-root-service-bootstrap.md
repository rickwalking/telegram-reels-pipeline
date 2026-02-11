# Story 1.8: Composition Root & Service Bootstrap

Status: done

## Story

As a developer,
I want the complete service wired together and running as a systemd daemon,
so that the pipeline starts on boot and is ready to process requests.

## Acceptance Criteria

1. Given the bootstrap module, when create_orchestrator() is called, then all adapters are instantiated and wired to Port Protocols and Pydantic BaseSettings loads config from .env
2. Given the main entry point, when python3 -m pipeline.app.main is run, then the daemon polls for queue items when idle
3. Given the EventBus, when the orchestrator is created, then the journal writer listener is registered

## Tasks / Subtasks

- [x] Task 1: Implement PipelineSettings with Pydantic BaseSettings
- [x] Task 2: Implement create_orchestrator() bootstrap function
- [x] Task 3: Implement Orchestrator container dataclass
- [x] Task 4: Implement main entry point with queue polling loop
- [x] Task 5: Write comprehensive tests (8 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 266 tests passing, 93.77% coverage, all linters clean
- Added pydantic-settings dependency
- PipelineSettings: env-based config with defaults, .env file support
- create_orchestrator(): wires all adapters, registers journal listener
- Orchestrator: mutable dataclass container for all components
- main.py: asyncio.run() with 5s queue polling, KeyboardInterrupt handler
- 8 new tests across 2 test files
- Review fix: CliBackend now implements ModelDispatchPort (dispatch() method), removed type: ignore
- Review fix: ReflectionLoop wired with min_qa_score from PipelineSettings
- Review fix: added dispatch() tests and ModelDispatchPort protocol check test

### File List

- src/pipeline/app/settings.py (NEW)
- src/pipeline/app/bootstrap.py (NEW)
- src/pipeline/app/main.py (NEW)
- tests/unit/app/__init__.py (NEW)
- tests/unit/app/test_settings.py (NEW)
- tests/unit/app/test_bootstrap.py (NEW)
- pyproject.toml (MODIFIED — added pydantic-settings)
