# Story 2.2: Router Agent — Elicitation & Smart Defaults

Status: done

## Story

As a user,
I want the pipeline to ask me quick clarifying questions or proceed with smart defaults,
so that I can give direction when I want to or just send a URL and go.

## Acceptance Criteria

1. Given a new run starts, when the Router Agent executes, then it parses the YouTube URL and asks 0-2 elicitation questions via Telegram ask_user (topic focus, duration preference)
2. Given the user provides topic focus, when the Router Agent processes the response, then the elicitation context is saved to the workspace for downstream agents
3. Given the user provides only a URL with no additional context, when the Router Agent applies smart defaults, then predefined defaults from pipeline configuration are used and the pipeline proceeds without further questions
4. Given a run is already in progress when a new URL arrives, when the queue consumer detects the active run, then the user is notified of queue position via Telegram

## Tasks / Subtasks

- [x] Task 1: Implement StageRunner (generic stage execution: agent -> QA -> recovery)
- [x] Task 2: Implement RouterHandler (elicitation flow, smart defaults)
- [x] Task 3: Add elicitation defaults to PipelineSettings
- [x] Task 4: Write comprehensive tests (19 tests)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Completion Notes List

- 338 tests passing, 92.02% coverage, all linters clean
- StageRunner: generic execute->QA->recovery cycle with event emission
- RouterHandler: 0-2 questions via Telegram, skip/defaults fallback, JSON artifact save
- PipelineSettings: added default_topic_focus and default_duration_preference
- Elicitation context saved as JSON in workspace/assets/

### File List

- src/pipeline/application/stage_runner.py (NEW)
- src/pipeline/application/router_handler.py (NEW)
- src/pipeline/app/settings.py (MODIFIED — added elicitation defaults)
- tests/unit/application/test_stage_runner.py (NEW)
- tests/unit/application/test_router_handler.py (NEW)
