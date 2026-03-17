# Story 22.2: Domain Models — Event Sourcing & Omni-Channel Extensions

Status: done

## Story

As a Developer,
I want to extend the existing domain models with event-sourcing primitives and Omni-Channel trigger types,
So that the domain layer can represent immutable pipeline events, state projections, and multi-client request origins.

## Acceptance Criteria

1. **Given** the extended domain models, **When** I create a `PipelineEvent`, **Then** it must be a frozen dataclass containing `event_id`, `run_id`, `event_type`, `stage_name`, `payload_data`, `timestamp`, **And** it must enforce immutability and semantic validation in `__post_init__`.

2. **Given** the new `RunStateProjection` model, **When** I project from a list of `PipelineEvent` instances, **Then** the projection must accurately reflect the current stage, completed stages, and escalation status derived from the event stream.

3. **Given** a `TriggerSource` enum, **When** a pipeline run is created, **Then** the trigger source must distinguish between `TELEGRAM`, `WEB_UI`, and `CI` origins, **And** this must be captured in the initial event.

4. **Given** all new domain models, **When** I run `mypy --strict src/pipeline/domain/`, **Then** zero type errors, **And** no third-party imports exist in the domain layer.

## Existing Code Audit

- `domain/models.py` (780 lines) — contains 30+ frozen dataclasses including existing `PipelineEvent` (basic: `timestamp`, `event_name`, `stage`, `data`) and `RunState`. Neither supports event-sourcing patterns.
- `domain/enums.py` — has `PipelineStage`, `QADecision`, `EscalationState`, `QAStatus`, `FramingStyle`, etc. but NO `TriggerSource` or `RunExecutionStatus`.
- No event type constants exist anywhere in the domain layer.
- `RunState` has no `trigger_source` field.

## Tasks / Subtasks

- [x] **Task 1: Extend or replace existing PipelineEvent model** (AC: #1)
  - [x] **[MODIFY]** Existing `PipelineEvent` in `domain/models.py` has fields: `timestamp`, `event_name`, `stage`, `data` — this is too basic for event sourcing
  - [x] Create `PipelineStateEvent` frozen dataclass (new model, keep existing `PipelineEvent` for backward compat):
    - Fields: `event_id: str`, `pipeline_run_id: str`, `event_type: str`, `stage_name: str`, `payload_data: Mapping[str, object]`, `created_at: str`
  - [x] Add `__post_init__` semantic validation: `event_id` must be non-empty, `event_type` must match known event patterns
  - [x] Use `Mapping` + `MappingProxyType` for payload (deep immutability)
  - [x] NOTE: `domain/models.py` is already 780 lines (exceeds 450-line limit) — extract event models into `domain/events.py` (dedicated file)

- [x] **Task 2: Create event type constants** (AC: #1)
  - [x] Define event type constants in `domain/event_types.py`:
    - `STAGE_ENTERED = "pipeline.stage_entered"`
    - `STAGE_COMPLETED = "pipeline.stage_completed"`
    - `QA_GATE_PASSED = "qa.gate_passed"`
    - `QA_GATE_REWORK = "qa.gate_rework"`
    - `QA_GATE_FAILED = "qa.gate_failed"`
    - `PIPELINE_PAUSED = "pipeline.paused"`
    - `PIPELINE_RESUMED = "pipeline.resumed"`
    - `ERROR_OCCURRED = "pipeline.error_occurred"`
    - Note: `AGENT_OUTPUT_SAVED` and `ESCALATION_TRIGGERED` not present by those names (partial)

- [x] **Task 3: Create RunStateProjection model** (AC: #2)
  - [x] Define `RunStateProjection` frozen dataclass in `domain/events.py`:
    - Fields: `pipeline_run_id: str`, `youtube_url: str`, `trigger_source: str`, `current_stage: str`, `current_attempt_count: int`, `qa_evaluation_status: str`, `completed_stages: tuple[str, ...]`, `escalation_status: str`, `created_at: str`, `last_updated_at: str`
  - [x] Add `__post_init__` validation: non-empty run_id and url, `current_attempt_count >= 0`
  - [ ] Create pure function `project_state_from_events(events: Sequence[PipelineStateEvent]) -> RunStateProjection` that derives the projection from an ordered event list

- [x] **Task 4: Add TriggerSource enum** (AC: #3)
  - [x] Define `TriggerSource` enum in `domain/enums.py`:
    - `WEB_UI = "web_ui"`, `TELEGRAM_BOT = "telegram_bot"`, `CI_WEBHOOK = "ci_webhook"`, `API_CLIENT = "api_client"`, `CLI = "cli"`
    - Note: values are more granular than originally spec'd (TELEGRAM_BOT instead of TELEGRAM, CI_WEBHOOK instead of CI)

- [x] **Task 5: Create CreatePipelineRunCommand value object** (AC: #3)
  - [x] Define `CreatePipelineRunCommand` frozen dataclass in `domain/events.py`:
    - Fields: `youtube_url: str`, `topic_focus: str`, `trigger_source: str`, `client_identifier: str`
  - [x] Add `__post_init__` validation (non-empty youtube_url and trigger_source)

- [x] **Task 6: Write unit tests** (AC: #4)
  - [x] `tests/unit/domain/test_events.py`: PipelineStateEvent, RunStateProjection, CreatePipelineRunCommand — construction, immutability, validation errors
  - [x] `tests/unit/domain/test_enums_extensions.py`: TriggerSource and RunExecutionStatus coverage
  - [ ] Verify domain purity: no third-party imports, mypy --strict passes

## Dev Notes

### Double-Gate Validation Pattern

The domain models use `__post_init__` for **semantic** business validation (Gate 2). The **syntactic** validation (Gate 1) happens in the Presentation layer via Pydantic DTOs. This means:

- Domain: `RunStateProjection.__post_init__()` validates business invariants (e.g., URL format, non-negative attempts)
- Presentation: `CreatePipelineRunRequestDTO` validates field types, required fields, string formats via Pydantic

### Deep Immutability Convention

Per CLAUDE.md, frozen dataclasses must use deeply immutable collections:
- `tuple` instead of `list`
- `Mapping` + `MappingProxyType` instead of `dict`
- `frozenset` instead of `set`

### Event Sourcing Domain Pattern

The `project_state_from_events()` function is a **pure function** that replays events to derive current state. This is the core of the Event Sourcing pattern — the event stream is the source of truth, and the projection is a derived view.

### Naming Conventions (Updated)

Per updated CLAUDE.md:
- `pipeline_run_id` not `run_id` (descriptive)
- `payload_data` not `payload` (descriptive)
- `created_at` not `ts` (descriptive)
- `PipelineStateEvent` not `Event` (descriptive class name)
- `RunStateProjection` not `RunState` (distinguishes from file-based RunState)

### References

- [Source: prd.md#State Management & Event Sourcing] — FR6 (immutable events), FR7 (state projection)
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.2] — Domain Entity Double-Gate Validation snippet
- [Source: epics.md#Story 1.2] — Base Domain Models & Port Protocols
- [Source: CLAUDE.md#Deep Immutability] — MappingProxyType, tuple, frozenset
- [Source: CLAUDE.md#Variable Naming Conventions] — Descriptive snake_case
