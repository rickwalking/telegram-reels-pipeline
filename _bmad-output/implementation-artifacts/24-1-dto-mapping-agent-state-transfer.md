# Story 24.1: DTO Mapping for Agent State Transfer

Status: ready-for-dev

## Story

As a Developer,
I want to create strict Pydantic DTOs for data transitioning between the AI Agents and the Domain,
So that all incoming JSON payloads from agents are syntactically validated before reaching the Application layer.

## Acceptance Criteria

1. **Given** the need for agents to save data (transcripts, layout decisions, content), **When** defining stage-specific output DTOs, **Then** Pydantic must strictly validate the data types, required fields, and constraints, **And** no field may use `Any` type.

2. **Given** a valid DTO, **When** a mapper function converts it to a domain entity, **Then** the domain entity's `__post_init__` must perform semantic business validation (Double-Gate Validation).

3. **Given** an invalid JSON payload from an agent, **When** the DTO validation fails, **Then** a structured error with field-level details must be returned, **And** the error must be actionable for the agent to self-correct.

4. **Given** all DTOs, **When** I run `mypy --strict`, **Then** zero type errors, **And** no `Any` types exist in any DTO definition.

## Existing Code Audit

- `presentation/dtos/run_dtos.py` — EXISTS with 3 DTOs:
  - `CreateRunRequestDTO`: has `youtube_url: HttpUrl`, `topic_focus`, `client_type`, `client_id`
  - `RunStateResponseDTO`: has `run_id`, `youtube_url`, `current_stage`, `status`, `stages_completed`, timestamps
  - `SaveStageDTO`: has `stage: str`, `payload: dict` — **uses `dict` which is effectively `Any` (banned per CLAUDE.md)**
- No stage-specific output DTOs exist.
- No DTO-to-domain mappers in presentation layer (the existing mapper is in `application/` which is a layer violation).
- No validation error response format for agents.
- No `ConfigDict(strict=True, extra="forbid")` on existing DTOs.

## Tasks / Subtasks

- [ ] **Task 1: Create base DTO patterns** (AC: #1, #4)
  - [ ] Create `src/pipeline/presentation/dtos/base_stage_output_dto.py`
  - [ ] Base class with common fields: `pipeline_run_id: str`, `stage_name: str`, `generated_at: str`
  - [ ] Use Pydantic `model_config = ConfigDict(strict=True, extra="forbid")`

- [ ] **Task 2: Create stage-specific output DTOs** (AC: #1)
  - [ ] `presentation/dtos/router_output_dto.py`: `RouterOutputDTO` — tier, elicitation answers, topic extraction
  - [ ] `presentation/dtos/research_output_dto.py`: `ResearchOutputDTO` — episode metadata, context summary
  - [ ] `presentation/dtos/transcript_output_dto.py`: `TranscriptOutputDTO` — selected moments, timestamps, narrative roles
  - [ ] `presentation/dtos/content_output_dto.py`: `ContentOutputDTO` — descriptions, hashtags, music suggestions
  - [ ] `presentation/dtos/layout_analysis_output_dto.py`: `LayoutAnalysisOutputDTO` — face positions, layout classification
  - [ ] `presentation/dtos/ffmpeg_encoding_plan_dto.py`: `FfmpegEncodingPlanDTO` — segments, crop regions, encoding params
  - [ ] `presentation/dtos/assembly_report_dto.py`: `AssemblyReportDTO` — final reel path, quality metrics
  - [ ] Each DTO has field-level validators and descriptive error messages

- [ ] **Task 3: Create DTO-to-domain mapper functions** (AC: #2)
  - [ ] Create `src/pipeline/presentation/dtos/mappers/` package
  - [ ] One mapper per stage: `map_router_dto_to_domain()`, `map_transcript_dto_to_domain()`, etc.
  - [ ] Each mapper: validates DTO (Gate 1), constructs domain entity (Gate 2 in `__post_init__`)
  - [ ] Mappers are pure functions — no side effects, no I/O

- [ ] **Task 4: Create validation error response format** (AC: #3)
  - [ ] Define `AgentValidationErrorDTO` with:
    - `error_type: str` (e.g., "validation_error")
    - `invalid_fields: list[FieldErrorDetailDTO]` with `field_name`, `error_message`, `received_value`
    - `suggested_correction: str | None`
  - [ ] Format designed for LLM consumption (agent self-correction)

- [ ] **Task 5: Write unit tests** (AC: #1, #2, #3, #4)
  - [ ] `tests/unit/presentation/test_router_output_dto.py`: valid/invalid payload handling
  - [ ] `tests/unit/presentation/test_transcript_output_dto.py`: timestamp validation
  - [ ] `tests/unit/presentation/test_dto_mappers.py`: round-trip DTO → domain entity
  - [ ] `tests/unit/presentation/test_validation_error_format.py`: structured error output
  - [ ] Verify all DTOs reject `extra` fields and enforce strict types

## Dev Notes

### Double-Gate Validation Flow

```
Agent JSON payload
    ↓
Gate 1: Pydantic DTO (syntactic)
    - Type checking (str, int, list[str])
    - Required field enforcement
    - Format validation (URL patterns, date formats)
    - Extra field rejection
    ↓
Gate 2: Domain Entity __post_init__ (semantic)
    - Business rule validation (valid stage transitions)
    - Cross-field consistency (start_time < end_time)
    - Domain invariant enforcement
```

### Agent-Friendly Error Messages

Since Claude agents consume these errors for self-correction, the error format should be explicit:

```json
{
  "error_type": "validation_error",
  "invalid_fields": [
    {
      "field_name": "moment_start_seconds",
      "error_message": "Must be a positive number less than video duration",
      "received_value": "-5.0"
    }
  ],
  "suggested_correction": "Set moment_start_seconds to a positive value within the video's timestamp range."
}
```

### Strict Pydantic Configuration

Per CLAUDE.md, `Any` is banned. All DTO fields must have explicit types:
- Use `str` not `Any` for JSON text
- Use `dict[str, str]` not `dict[str, Any]` for known structures
- Use `list[SpecificItemDTO]` not `list[Any]` for nested collections

### References

- [Source: prd.md#AI Agent Interaction] — FR9, FR10, FR11 (agent state read/write/validation)
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.1] — FastMCP Tool with DTO validation
- [Source: epics.md#Story 3.1] — DTO Mapping for Agent State Transfer
- [Source: CLAUDE.md#Double-Gate Validation] — Pydantic + __post_init__ pattern
- [Source: CLAUDE.md#Strict Typing] — Any is banned
