# Story 17-7: Await Gate Pipeline Stage

## Context

The Veo3 generation runs asynchronously alongside Stages 5-6 (Story 17-4). Before Assembly (Stage 7) can weave B-roll clips into the final reel, the pipeline must wait for all Veo3 jobs to resolve. This story introduces `VEO3_AWAIT` as a formal pipeline stage — not a hidden hook, but a first-class checkpointable state in the FSM.

This design decision was validated by codereview: without a formal stage, the 300s blocking operation would be invisible to the FSM. A crash during the wait would lose all B-roll with no recovery path. Making it a `PipelineStage` ensures the system checkpoints before and after the gate, and can resume by re-checking `veo3/jobs.json` on restart.

The await gate depends on Story 17-6's `crop_and_validate()` to process each downloaded clip.

## Story

As a pipeline developer,
I want a formal `VEO3_AWAIT` pipeline stage that blocks before Assembly until all Veo3 jobs resolve or timeout,
so that the await is checkpoint-recoverable and Assembly has access to all available generated clips.

## Acceptance Criteria

1. Given the pipeline stage enum, when `VEO3_AWAIT` is added, then it appears in `_STAGE_SEQUENCE` between `FFMPEG_ENGINEER` and `ASSEMBLY`

2. Given `domain/transitions.py`, when the FSM is updated, then it includes:
   - `(PipelineStage.FFMPEG_ENGINEER, "qa_pass") → PipelineStage.VEO3_AWAIT`
   - `(PipelineStage.VEO3_AWAIT, "stage_complete") → PipelineStage.ASSEMBLY`

3. Given `pipeline_runner.py`, when `VEO3_AWAIT` is the current stage, then it executes await gate logic directly (no QA gate, no agent — this is a non-agent stage)

4. Given the await gate, when it starts, then it reads `veo3/jobs.json` to check job resolution status

5. Given active jobs, when polling, then it uses exponential backoff until all jobs resolved or `VEO3_TIMEOUT_S` from settings is exceeded

6. Given completed jobs, when downloading clips, then each clip is processed via `crop_and_validate()` from Story 17-6

7. Given job evaluation, when all jobs completed, then gate proceeds to Assembly with all clips available

8. Given job evaluation, when some jobs failed, then gate proceeds to Assembly with available clips only (partial success)

9. Given job evaluation, when all jobs failed or timeout exceeded, then gate proceeds to Assembly without B-roll (emergency fallback, no pipeline failure)

10. Given `veo3/jobs.json`, when the gate completes, then it is atomically updated with final status for each job

11. Given pipeline state, when the gate starts and completes, then checkpoints are saved (crash during 300s wait recovers by re-checking `veo3/jobs.json` on resume)

12. Given the EventBus, when the gate runs, then it emits: `veo3.gate.started`, `veo3.gate.completed` (with clip count), `veo3.gate.timeout` (if applicable)

13. Given a run with no `veo3/` folder (generation was skipped or no prompts), when the gate runs, then it is a no-op and proceeds immediately to Assembly

## Tasks

- [ ] Task 1: Add `VEO3_AWAIT` to `PipelineStage` enum
- [ ] Task 2: Insert `VEO3_AWAIT` into `_STAGE_SEQUENCE` between FFMPEG_ENGINEER and ASSEMBLY
- [ ] Task 3: Add FSM transitions in `domain/transitions.py` for VEO3_AWAIT state
- [ ] Task 4: Modify `pipeline_runner.py` to handle VEO3_AWAIT as non-agent stage
- [ ] Task 5: Create `application/veo3_await_gate.py` with await gate logic
- [ ] Task 6: Implement polling with exponential backoff
- [ ] Task 7: Implement clip download + `crop_and_validate()` call per clip
- [ ] Task 8: Implement three evaluation paths (all pass, partial, all fail)
- [ ] Task 9: Implement checkpoint save before/after gate
- [ ] Task 10: Implement EventBus event emission
- [ ] Task 11: Implement crash recovery (resume re-checks jobs.json)
- [ ] Task 12: Integration tests for all three evaluation paths
- [ ] Task 13: Integration test for crash recovery scenario
- [ ] Task 14: Integration test for no-veo3-folder no-op path

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/domain/transitions.py` | Add VEO3_AWAIT state + transition entries to pipeline FSM | Domain FSM |
| `src/pipeline/application/pipeline_runner.py` | Insert VEO3_AWAIT in stage sequence + non-agent handler | Application layer |
| `src/pipeline/application/veo3_await_gate.py` | New file — await gate logic with polling, download, evaluation | Application layer |
| `tests/unit/domain/test_transitions_veo3.py` | New file — FSM transition tests for VEO3_AWAIT | Tests |
| `tests/integration/test_veo3_await_gate.py` | New file — gate evaluation paths + recovery tests | Tests |

## Technical Notes

- The `PipelineStage` enum likely lives in `domain/models.py` or a separate `domain/enums.py` — check existing code for exact location
- The pipeline runner's stage loop iterates `_STAGE_SEQUENCE`. The handler for VEO3_AWAIT should be a conditional branch: `if stage == PipelineStage.VEO3_AWAIT: await self._run_veo3_gate(...)` — similar to how DELIVERY is handled as a special case
- Exponential backoff: start at 5s, double each poll, cap at 30s. Reset to 5s when any job status changes
- The gate should respect the background polling worker from Story 17-4 — by the time the gate fires, most/all jobs may already be resolved. The gate just waits for any stragglers
- Crash recovery: on resume, the gate checks `veo3/jobs.json`. Jobs marked `completed` with existing `video_path` are skipped. Jobs still `generating` are re-polled. Jobs marked `failed`/`timed_out` are accepted as-is

## Definition of Done

- `VEO3_AWAIT` is a formal pipeline stage in the FSM
- Await gate handles all three evaluation paths + crash recovery
- Checkpoints saved before and after gate
- EventBus events emitted
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
