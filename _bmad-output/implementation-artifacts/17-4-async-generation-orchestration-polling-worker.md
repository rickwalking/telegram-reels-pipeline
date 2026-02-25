# Story 17-4: Async Generation Orchestration & Polling Worker

## Context

After Stage 4 (CONTENT) completes, the Content Creator has produced `publishing-assets.json` with enriched `veo3_prompts[]`. This story creates the orchestration service that reads those prompts, fires parallel async Veo3 API calls via `VideoGenerationPort`, and runs a polling worker to track job status. Generation runs concurrently with Stages 5-6, exploiting the natural pipeline gap as free generation time.

The orchestration service lives in the application layer. The polling worker uses adaptive backoff (fast when status changes, patient when idle). Job state is tracked per-clip in `veo3/jobs.json` using atomic writes.

## Story

As a pipeline developer,
I want an orchestration service that fires parallel Veo3 API calls after Stage 4 and a polling worker that tracks job status with adaptive backoff,
so that video generation runs concurrently with Stages 5-6 and job state is reliably tracked.

## Acceptance Criteria

1. Given Stage 4 (CONTENT) completes, when the orchestration service fires, then it reads `veo3_prompts[]` from `publishing-assets.json` in the run workspace

2. Given `veo3_prompts[]` contains N prompts, when N exceeds `VEO3_CLIP_COUNT` from settings, then only the first `VEO3_CLIP_COUNT` prompts are submitted

3. Given valid prompts, when `submit_job()` is called, then all jobs fire as parallel async calls via `VideoGenerationPort` (not sequential)

4. Given the run workspace, when generation starts, then a `veo3/` subfolder is created and `veo3/jobs.json` is written with initial per-clip status using atomic writes (write-to-tmp + rename)

5. Given active jobs, when the polling worker runs, then it uses adaptive backoff: shorter intervals when job status changes (e.g., PENDING → GENERATING), longer intervals when status is stable

6. Given `veo3/jobs.json`, when any job's status changes, then the file is atomically updated with the new status

7. Given per-clip independent tracking, when some jobs fail, then remaining jobs continue unaffected (partial success beats all-or-nothing)

8. Given idempotent keys, when each job is submitted, then the key follows the `{run_id}_{variant}` pattern from `make_idempotent_key()`

9. Given `pipeline_runner.py`, when Stage 4 completes, then the async generation is fired as a non-blocking background task that runs alongside Stages 5-6

## Tasks

- [ ] Task 1: Create `application/veo3_orchestrator.py` with `Veo3Orchestrator` class
- [ ] Task 2: Implement `start_generation()` — read prompts, cap at CLIP_COUNT, fire parallel async calls
- [ ] Task 3: Implement `veo3/` subfolder creation in run workspace
- [ ] Task 4: Implement `veo3/jobs.json` initial write with atomic writes
- [ ] Task 5: Implement polling worker with adaptive backoff strategy
- [ ] Task 6: Implement atomic status updates to `jobs.json` on poll results
- [ ] Task 7: Modify `pipeline_runner.py` to fire async generation after CONTENT stage completes (non-blocking)
- [ ] Task 8: Integration tests with `FakeVeo3Adapter` — parallel submission, polling, partial failure

## Files Affected

| File | Change | Type |
|------|--------|------|
| `src/pipeline/application/veo3_orchestrator.py` | New file — `Veo3Orchestrator` with `start_generation()` + polling worker | Application layer |
| `src/pipeline/application/pipeline_runner.py` | Add post-Stage-4 non-blocking async hook to fire `Veo3Orchestrator.start_generation()` | Application layer |
| `tests/unit/application/test_veo3_orchestrator.py` | New file — orchestration + polling tests with fake adapter | Tests |
| `tests/integration/test_veo3_generation_flow.py` | New file — end-to-end generation flow with fake adapter | Tests |

## Technical Notes

- The post-Stage-4 hook in `pipeline_runner.py` should use `asyncio.create_task()` or equivalent to fire generation without blocking the stage loop. Stages 5-6 proceed immediately
- The polling worker is an async loop that runs in the background alongside stages 5-6. It does NOT block pipeline progression
- `veo3/jobs.json` schema: `{"jobs": [{"idempotent_key": "...", "variant": "...", "status": "pending", "video_path": null, "error_message": null}]}`
- Atomic writes follow existing project convention: write to `.tmp` file, then `os.rename()` for atomic replacement
- The `Veo3Orchestrator` takes `VideoGenerationPort` as a constructor dependency (injected by composition root)
- If `veo3_prompts[]` is empty or missing, orchestration is a no-op (no error, no `veo3/` folder created)

## Definition of Done

- `Veo3Orchestrator` in application layer with parallel async generation + polling
- `pipeline_runner.py` fires generation non-blocking after Stage 4
- Atomic `veo3/jobs.json` state tracking
- All tests pass, linters clean, mypy clean
- Min 80% coverage on new code
