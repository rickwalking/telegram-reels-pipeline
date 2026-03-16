# Story 26.5: Automated QA Reflection Loop (Event-Sourced)

Status: ready-for-dev

## Story

As a System Operator,
I want an automated LLM QA gate to evaluate agent outputs before moving to the next stage,
So that errors or poor choices are caught early and reworked automatically.

## Acceptance Criteria

1. **Given** an agent has produced an output, **When** the QA stage is triggered, **Then** a Critic model must evaluate the output against predefined criteria, **And** each QA evaluation must be recorded as an event in MongoDB.

2. **Given** a QA evaluation result of REWORK, **When** the loop retries, **Then** the previous QA feedback must be included in the agent's context for the rework attempt, **And** the attempt count must be tracked in events.

3. **Given** the maximum rework attempts (3) are exhausted, **When** the QA still fails, **Then** the pipeline must select the best-of-three outputs or escalate, **And** a `qa.gate_failed` event must be emitted.

4. **Given** the existing `ReflectionLoop` class, **When** integrating, **Then** it must emit events for every QA evaluation via `PipelineEventEmitterService`, **And** the QA critique payload must be stored in MongoDB.

## Tasks / Subtasks

- [ ] **Task 1: Update ReflectionLoop for event emission** (AC: #1, #4)
  - [ ] Modify `application/reflection_loop.py` to accept `PipelineEventEmitterService`
  - [ ] After each QA evaluation: emit `qa.gate_passed`, `qa.gate_rework`, or `qa.gate_failed` event
  - [ ] Event payload includes full `QACritique` data (score, blockers, prescriptive fixes)
  - [ ] Track attempt number in each event

- [ ] **Task 2: Create QA evaluation use case** (AC: #1, #2)
  - [ ] Create `src/pipeline/application/use_cases/evaluate_stage_output_use_case.py`
  - [ ] `EvaluateStageOutputUseCase` with injected: `ModelDispatchPort`, `PipelineEventEmitterService`
  - [ ] Loads gate criteria for the specific stage
  - [ ] Dispatches evaluation to Critic model
  - [ ] Parses and validates critique via `QaCritiqueDTO`
  - [ ] Returns `Result[QACritique, DomainError]`

- [ ] **Task 3: Create QA context builder for rework** (AC: #2)
  - [ ] When QA returns REWORK, build rework context:
    - Original agent output
    - QA critique with prescriptive fixes
    - Attempt number
    - Prior attempt history (from event store)
  - [ ] Pass this context to the agent for the rework attempt

- [ ] **Task 4: Implement best-of-three selection** (AC: #3)
  - [ ] When 3 attempts fail: query event store for all attempt outputs
  - [ ] Select the attempt with the highest QA score
  - [ ] Emit `qa.best_of_three_selected` event with the chosen attempt number
  - [ ] Proceed with the best output rather than escalating (unless all scores below threshold)

- [ ] **Task 5: Create QaCritiqueDTO** (AC: #1)
  - [ ] `presentation/dtos/qa_critique_dto.py`:
    - `decision: str` (PASS, REWORK, FAIL)
    - `score: int` (0-100)
    - `gate_name: str`
    - `attempt_number: int`
    - `blockers: list[QaBlockerDTO]` (severity, description)
    - `prescriptive_fixes: list[str]`
    - `confidence_score: float` (0.0-1.0)
  - [ ] Strict validation: score range, valid decision values

- [ ] **Task 6: Write BDD feature file** (AC: #1, #2, #3)
  - [ ] Create `tests/bdd/features/qa_reflection_loop.feature`:
    - Scenario: QA passes on first attempt
    - Scenario: QA reworks with prescriptive feedback
    - Scenario: QA exhausts attempts and selects best-of-three
  - [ ] Step definitions with faked model dispatch and event store

- [ ] **Task 7: Write unit tests** (AC: #1, #2, #3, #4)
  - [ ] `tests/unit/application/test_evaluate_stage_output_use_case.py`
  - [ ] `tests/unit/application/test_reflection_loop_event_emission.py`
  - [ ] Test: each evaluation emits correct event type
  - [ ] Test: rework context includes prior feedback
  - [ ] Test: best-of-three selects highest score

## Dev Notes

### Generator-Critic Pattern with Event Sourcing

The existing ReflectionLoop implements the Generator-Critic pattern. The refactor adds event sourcing:

```
Attempt 1:
  Generator (Agent) produces output
  Critic (QA Model) evaluates → REWORK (score: 72)
  Event: qa.gate_rework { score: 72, attempt: 1, prescriptive_fixes: [...] }

Attempt 2:
  Generator receives rework context (with prior QA feedback)
  Critic evaluates → REWORK (score: 78)
  Event: qa.gate_rework { score: 78, attempt: 2, prescriptive_fixes: [...] }

Attempt 3:
  Generator receives both prior feedbacks
  Critic evaluates → REWORK (score: 81)
  Event: qa.gate_rework { score: 81, attempt: 3 }

Best-of-three:
  Select attempt 3 (score: 81)
  Event: qa.best_of_three_selected { selected_attempt: 3, score: 81 }
```

### NFR Compliance

- NFR-R3: QA rework convergence average ≤1 cycle per gate (max 3 attempts)
- Events enable post-hoc analysis of QA convergence rates via DVR

### References

- [Source: prd.md#Core Processing] — FR20 (automated QA evaluation gates)
- [Source: prd.md#Non-Functional Requirements] — NFR-R3 (QA convergence)
- [Source: epics.md#Story 5.5] — Automated QA Reflection Loop
- [Source: architecture.md#Decisions] — Generator-Critic reflection loop, max 3 attempts
- [Source: CLAUDE.md#Generator-Critic QA] — ReflectionLoop with max 3 attempts
