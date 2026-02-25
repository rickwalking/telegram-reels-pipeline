# Story 10.1: CLI Elicitation Loop — Interactive Questions in Terminal

Status: done

## Problem

When running the pipeline via `scripts/run_cli.py`, the Router agent may produce elicitation questions (e.g., "Please share the YouTube video URL") in its `router-output.json`. Currently, the pipeline treats this as a completed output and sends it through the QA gate, which fails it (score 25) because `url: null` makes the output incomplete. The pipeline escalates and stops.

In Telegram mode, the `RouterHandler` handles this by asking questions via the `MessagingPort`. But the CLI runner bypasses `RouterHandler` entirely and calls `StageRunner` directly.

### Reproduction

```bash
poetry run python scripts/run_cli.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --message "create a short about TOPIC" --timeout 600
```

If the Router agent decides to ask an elicitation question instead of proceeding with defaults, the QA gate scores the output as FAIL (25) and the pipeline stops immediately.

### Evidence

From run `20260211-191521-a97fec`:
```json
{
  "url": null,
  "topic_focus": "N8N and Willzinho bot",
  "elicitation_questions": [
    "Please share the YouTube video URL you'd like me to create the short from."
  ]
}
```
QA gate scored this 25 (FAIL) with escalation.

## Story

As a CLI user,
I want the pipeline to pause and ask me elicitation questions in the terminal when the Router needs clarification,
so that the pipeline can proceed with my answers instead of failing.

## Acceptance Criteria

1. Given the Router produces `elicitation_questions` in its output, when running in CLI mode, then the questions are displayed in the terminal and the user is prompted for answers via stdin
2. Given the user provides answers to elicitation questions, when the answers are collected, then the Router is re-run with enriched elicitation context including the user's answers
3. Given the elicitation loop runs, when the Router still produces questions after 2 rounds, then the pipeline applies smart defaults and proceeds (max 2 rounds)
4. Given the Router produces an empty `elicitation_questions` array, when the output includes a valid URL, then the pipeline proceeds normally without prompting
5. Given a non-interactive environment (piped stdin), when the Router produces questions, then smart defaults are applied automatically without blocking

## Architecture Decision (Validated with Codex 5.3)

### Phase 1: Immediate CLI Containment (this story)
- After Router stage completes in `run_cli.py`, parse `router-output.json`
- If `elicitation_questions` is non-empty, display questions and prompt via stdin
- Re-run Router with enriched context (max 2 rounds)
- Guard for non-interactive stdin (detect if TTY, fall back to defaults)

### Phase 2: Application-Layer Refactor (future story)
- Create `RouterInteractionCoordinator` in application layer
- Use `MessagingPort` with CLI adapter and Telegram adapter
- Wire both `run_cli.py` and `PipelineRunner` through the coordinator
- Deprecate direct `StageRunner` call for Router stage

### Why Re-run Instead of Patch
- Re-running the Router preserves its internal logic for revision classification, defaults, and schema validation
- Direct patching bypasses agent logic and risks inconsistent state
- The Router is fast (~40s), so re-running is acceptable

## Tasks / Subtasks

- [x] Task 1: Add `_handle_router_elicitation()` to `run_cli.py` — parse router output, detect questions, prompt user, merge answers into context
- [x] Task 2: Add TTY detection guard — if stdin is not a terminal, skip prompting and use smart defaults
- [x] Task 3: Implement bounded loop (max 2 rounds) with no-progress detection
- [x] Task 4: Persist elicitation answers to workspace as `elicitation-context.json`
- [x] Task 5: Update router QA gate criteria prompt to not hard-fail when `url=null` but valid elicitation questions exist (treat as "interaction-needed" state)
- [x] Task 6: Write tests — elicitation loop happy path, max rounds cap, non-interactive mode, empty questions skip
- [x] Task 7: Harden `--resume` / `--start-stage` CLI args (validated with Gemini 2.5 Pro + Codex 5.3 consensus)
  - [x] 7a: Add `_validate_cli_args()` — hard error if `--resume` path doesn't exist (never silently create new workspace)
  - [x] 7b: Hard error if `--start-stage > 1` without `--resume` (flag dependency enforcement)
  - [x] 7c: Range validation — `--start-stage` must be 1-7, reject 0, negatives, and > 7
  - [x] 7d: Auto-detect resume stage — when `--resume` is used without `--start-stage`, infer last completed stage from workspace artifacts. Reuse `crash_recovery.py` `stages_completed` logic to avoid duplicating heuristics. `--start-stage` remains as explicit override.
  - [x] 7e: Clear error messages to stderr with suggested correct usage (e.g., "Did you mean: --resume /path --start-stage N?")
  - [x] 7f: Write tests — missing resume path error, start-stage without resume error, range validation, auto-detect happy path, auto-detect with explicit override

## Edge Cases

- Non-interactive stdin (CI/piped): must not block; apply defaults
- Repeated identical questions: detect no-progress and stop after 2 rounds
- User enters empty/invalid answers: treat as skip, apply defaults
- Conflicting URL sources (CLI arg vs elicited answer): CLI arg takes precedence
- EOF on stdin: graceful exit with defaults applied
- `--resume` path doesn't exist: hard error, not silently start fresh (burned 25 min of API calls). Consensus: all 3 reviewers rated this critical.
- `--start-stage > 1` without `--resume`: hard error (flag dependency). No valid use case for skipping stages without a workspace.
- `--start-stage` out of range (0, negative, > 7): hard error with valid range shown in message
- `--resume` without `--start-stage`: auto-detect last completed stage from workspace artifacts via `crash_recovery.py` logic. If detection fails, error with list of found artifacts and ask user to specify `--start-stage` explicitly.

## Task 7 — Consensus Findings (Gemini 2.5 Pro + Codex 5.3)

### Unanimous (implement all)
- Hard error when `--resume` path doesn't exist — never silently create new workspace
- Hard error when `--start-stage > 1` without `--resume`
- Range validation for `--start-stage` (1-7)
- Clear error messages to stderr with suggested correct usage

### Majority (implement — 2 of 3 agreed)
- **Auto-detect resume stage**: When `--resume` is used without `--start-stage`, infer from workspace artifacts. Codex 5.3 identified that `crash_recovery.py` already has `stages_completed` logic — reuse it instead of building new heuristics. `--start-stage` remains as explicit override. (Gemini "against" dissented: called it "magic behavior" that's hard to debug when it guesses wrong.)

### Deferred (not in scope)
- Confirmation gate for new runs — hard errors cover the dangerous cases sufficiently
- `--dry-run` mode — nice-to-have UX polish, not essential for bug fix
- Workspace listing/inspection — future enhancement

## Technical Notes

- `RouterHandler` (application layer) exists but is pre-stage and static-question oriented — not designed for dynamic post-router JSON-question flow
- `PipelineRunner` also calls `StageRunner` directly without `RouterHandler` wiring
- QA FAIL on router short-circuits retries via `ReflectionLoop` line 115
- The `elicitation_questions` field is part of the router agent's output schema, not the domain model
