# Story 1.4: QA Reflection Loop

Status: done

## Story

As a developer,
I want QA gates that validate stage outputs with prescriptive feedback and automatic rework,
so that quality is enforced autonomously with minimal human intervention. (FR20-FR24)

## Acceptance Criteria

1. Given an agent produces an artifact, when the ReflectionLoop evaluates it against gate criteria, then a QACritique is returned matching the Pydantic-validated schema (decision, score, gate, attempt, blockers, prescriptive_fixes, confidence)
2. Given a QA gate returns REWORK with prescriptive feedback, when the reflection loop retries, then the agent receives the exact fix instructions from the previous critique and up to 3 attempts are made (hard cap)
3. Given 3 attempts all fail QA, when the best-of-three selector evaluates, then the highest-scoring attempt is selected and the pipeline continues
4. Given all automated QA recovery is exhausted (score below minimum threshold), when escalation is triggered, then the user is notified via Telegram with QA feedback summary and the pipeline pauses awaiting user guidance

## Tasks / Subtasks

- [x] Task 1: Implement ReflectionLoop in application layer (AC: 1, 2)
  - [x] 1.1 Create reflection_loop.py with ReflectionLoop class accepting AgentExecutionPort and ModelDispatchPort
  - [x] 1.2 Implement evaluate() method that calls ModelDispatchPort.dispatch() and parses QACritique
  - [x] 1.3 Implement run() method with retry loop (up to MAX_QA_ATTEMPTS) passing prescriptive fixes
- [x] Task 2: Implement best-of-three selector (AC: 3)
  - [x] 2.1 Add select_best() method that picks highest-scoring QACritique from attempts
  - [x] 2.2 Return the best attempt's artifacts when all 3 fail
- [x] Task 3: Implement escalation detection (AC: 4)
  - [x] 3.1 Add minimum score threshold constant (MIN_SCORE_THRESHOLD = 40)
  - [x] 3.2 Return escalation signal when best score is below threshold
- [x] Task 4: Add QAError to domain error hierarchy
  - [x] 4.1 Add QAError subclass of PipelineError
- [x] Task 5: Write comprehensive unit tests
  - [x] 5.1 Tests for evaluate() with PASS/REWORK/FAIL responses
  - [x] 5.2 Tests for retry loop with prescriptive feedback passing
  - [x] 5.3 Tests for best-of-three selection
  - [x] 5.4 Tests for escalation detection
  - [x] 5.5 Tests for edge cases (parse errors, empty responses)

## Dev Notes

- Application layer: imports domain only (no third-party)
- ReflectionLoop depends on AgentExecutionPort and ModelDispatchPort (both Protocol interfaces)
- QACritique already defined in domain/models.py with frozen dataclass
- MAX_QA_ATTEMPTS = 3 already defined in domain/transitions.py
- Use Pydantic for parsing QA model responses into QACritique
- Actually, QACritique is a frozen dataclass. Use json.loads + manual construction to stay in application layer (no Pydantic import)
- Actually we CAN use Pydantic in infrastructure layer. But ReflectionLoop is application layer. Use a port for parsing or parse manually with json.loads.
- Pattern: ReflectionLoop.run() returns a ReflectionResult dataclass with the best critique + artifacts + whether escalation is needed

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.4]
- [Source: src/pipeline/domain/models.py - QACritique dataclass]
- [Source: src/pipeline/domain/transitions.py - MAX_QA_ATTEMPTS]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

- 192 tests passing, 97.62% coverage, all linters clean (black, ruff, mypy)
- ReflectionLoop uses TYPE_CHECKING guard for port imports (application layer rule)
- QACritique parsing uses json.loads + manual construction (no Pydantic in application layer)
- Added ReflectionResult frozen dataclass to domain/models.py
- Added QAError to domain/errors.py
- Markdown code fence stripping in _parse_critique for LLM response robustness
- 23 new tests covering: parse critique, select best, evaluate, full run loop, escalation
- Review fix: min_score_threshold now configurable via constructor (wired from settings)
- Review fix: added test for custom min_score_threshold

### File List

- src/pipeline/application/reflection_loop.py (NEW)
- src/pipeline/domain/errors.py (MODIFIED — added QAError)
- src/pipeline/domain/models.py (MODIFIED — added ReflectionResult)
- tests/unit/application/test_reflection_loop.py (NEW)

