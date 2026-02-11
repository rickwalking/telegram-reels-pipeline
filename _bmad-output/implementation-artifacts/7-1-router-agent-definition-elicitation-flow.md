# Story 7.1: Router Agent Definition & Elicitation Flow

Status: ready-for-dev

## Story

As a pipeline developer,
I want the Router Agent definition and supporting knowledge files written,
So that the Router stage can interpret user URLs, ask targeted elicitation questions, and route revision requests to the correct pipeline stage.

## Acceptance Criteria

1. **Given** `agents/router/agent.md` exists and is non-empty,
   **When** PromptBuilder reads it for the ROUTER stage,
   **Then** it contains a complete agent persona, role description, input/output contracts, and behavioral instructions for Claude.

2. **Given** a user sends a YouTube URL with no additional context,
   **When** the Router Agent executes,
   **Then** it extracts the URL, determines if elicitation questions are needed (0-2 questions about topic focus, duration preference, specific moment),
   **And** outputs a structured JSON with: `url`, `elicitation_questions` (array), `defaults_applied` (dict).

3. **Given** a user sends a revision request (e.g., "make it longer", "different speaker"),
   **When** the Router Agent executes,
   **Then** it interprets the feedback, classifies the RevisionType (EXTEND_MOMENT, FIX_FRAMING, DIFFERENT_MOMENT, ADD_CONTEXT),
   **And** outputs routing instructions for the correct downstream agent.

4. **Given** `agents/router/elicitation-flow.md` exists,
   **When** the Router Agent references it,
   **Then** it contains the decision tree for when to ask vs. use defaults, question templates, and timeout handling.

5. **Given** `agents/router/revision-interpretation.md` exists,
   **When** the Router Agent processes revision requests,
   **Then** it contains mapping rules from natural language feedback to RevisionType enum values, with examples.

## Tasks / Subtasks

- [ ] Task 1: Write `agents/router/agent.md` (AC: #1, #2, #3)
  - [ ] Agent persona: "Router" — the intake coordinator
  - [ ] Role: Parse user input, extract URL, determine elicitation needs, route revisions
  - [ ] Input contract: raw Telegram message text, optional prior run context
  - [ ] Output contract: JSON with `url`, `topic_focus`, `duration_preference`, `revision_type`, `routing_target`
  - [ ] Behavioral rules: ask max 2 questions, use defaults after 60s timeout, never proceed without valid URL
  - [ ] Include reference to elicitation-flow.md and revision-interpretation.md

- [ ] Task 2: Write `agents/router/elicitation-flow.md` (AC: #4)
  - [ ] Decision tree: URL only → check defaults → ask 0-2 questions
  - [ ] Question templates: "What topic should the Reel focus on?", "How long should the clip be? (60-90 seconds)"
  - [ ] Default values: topic_focus=null (auto-detect), duration_preference=75s
  - [ ] Timeout behavior: proceed with defaults after 60s of no response

- [ ] Task 3: Write `agents/router/revision-interpretation.md` (AC: #5)
  - [ ] Mapping table: natural language → RevisionType
  - [ ] Examples: "make it longer" → EXTEND_MOMENT, "show the other speaker" → FIX_FRAMING, "pick a different part" → DIFFERENT_MOMENT, "add more context" → ADD_CONTEXT
  - [ ] Edge cases: ambiguous feedback → ask clarifying question
  - [ ] Routing targets: which pipeline stage to re-execute for each revision type

## Dev Notes

### Output JSON Schema

The Router Agent must output valid JSON that the pipeline can parse:

```json
{
  "url": "https://youtube.com/watch?v=...",
  "topic_focus": "AI safety debate",
  "duration_preference": 75,
  "revision_type": null,
  "routing_target": null,
  "elicitation_questions": []
}
```

For revision requests:
```json
{
  "url": null,
  "revision_type": "EXTEND_MOMENT",
  "routing_target": "TRANSCRIPT",
  "revision_context": "User wants 15 more seconds of context before the selected moment"
}
```

### Integration Points

- **Input**: Raw text from Telegram message (via `QueueItem.url` and `QueueItem.topic_focus`)
- **Output**: Parsed by `PipelineRunner._build_request()` for downstream stages
- **Elicitation**: Questions sent via `MessagingPort.ask_user()`, responses added to `elicitation_context`
- **Revisions**: Classified by `RevisionRouter` in `application/revision_router.py`

### PRD Functional Requirements

- FR1: Trigger via YouTube URL
- FR2: 0-2 elicitation questions
- FR3: Smart defaults when no context
- FR33: Interpret revision feedback and route

### File Locations

```
telegram-reels-pipeline/agents/router/agent.md                    # Main agent definition
telegram-reels-pipeline/agents/router/elicitation-flow.md          # Elicitation decision tree
telegram-reels-pipeline/agents/router/revision-interpretation.md   # Revision routing rules
```

### References

- [Source: prd.md#FR1-FR3, FR33] — Functional requirements
- [Source: pipeline_runner.py#_STAGE_DISPATCH] — Router stage mapping
- [Source: domain/enums.py#RevisionType] — EXTEND_MOMENT, FIX_FRAMING, DIFFERENT_MOMENT, ADD_CONTEXT
- [Source: application/revision_router.py] — RevisionRouter that consumes Router output

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
