# Story 25.3: Historical Event Scrubber (Pipeline DVR)

Status: ready-for-dev

## Story

As a System Operator,
I want to view a timeline of all events that occurred during a specific pipeline run,
So that I can retroactively debug what happened or see exactly how long each stage took.

## Acceptance Criteria

1. **Given** a completed or failed pipeline run, **When** I navigate to its DVR view, **Then** the UI must fetch the list of events from `GET /api/runs/{pipeline_run_id}/events`, **And** render them in a chronological timeline.

2. **Given** the DVR timeline, **When** I click on a specific event, **Then** the detail panel must show the event's full JSON payload, metadata, and timing information.

3. **Given** the DVR timeline, **When** I hover over stage boundaries, **Then** the UI must show the duration of each stage and any QA rework cycles.

4. **Given** the API endpoint, **When** queried, **Then** it must return paginated events with support for `?offset=N&limit=M` query parameters.

## Tasks / Subtasks

- [ ] **Task 1: Create events list API endpoint** (AC: #1, #4)
  - [ ] Add `GET /api/runs/{pipeline_run_id}/events` to router
  - [ ] Create `PipelineEventListResponseDTO` with pagination metadata
  - [ ] Create `PipelineEventItemDTO` with: `event_id`, `event_type`, `stage_name`, `created_at`, `payload_summary`
  - [ ] Create `ListPipelineEventsUseCase` — queries event store with pagination
  - [ ] Support query params: `offset` (default 0), `limit` (default 50, max 200)

- [ ] **Task 2: Create event detail API endpoint** (AC: #2)
  - [ ] Add `GET /api/runs/{pipeline_run_id}/events/{event_id}` to router
  - [ ] Create `PipelineEventDetailResponseDTO` with full payload
  - [ ] Return 404 if event not found

- [ ] **Task 3: Create DVR timeline component** (AC: #1, #3)
  - [ ] Create `frontend/src/components/PipelineDvrTimeline.tsx`
  - [ ] Render events as a vertical timeline with:
    - Stage boundary markers (colored by stage)
    - Event dots (sized by importance: stage transitions large, QA events medium)
    - Duration labels between stage boundaries
    - QA rework cycle indicators (loop arrows)
  - [ ] Highlight errors in red, successes in green

- [ ] **Task 4: Create event detail panel** (AC: #2)
  - [ ] Create `frontend/src/components/EventDetailPanel.tsx`
  - [ ] Side panel or modal that opens when clicking a timeline event
  - [ ] Display: event type, timestamp, stage, full JSON payload
  - [ ] Syntax-highlighted JSON viewer
  - [ ] Copy-to-clipboard button for payload

- [ ] **Task 5: Create Pipeline DVR page** (AC: #1, #2, #3)
  - [ ] Create `frontend/src/pages/PipelineDvrPage.tsx`
  - [ ] Layout: timeline on left, detail panel on right
  - [ ] Stage duration summary at top (bar chart showing time per stage)
  - [ ] Infinite scroll or "Load More" for paginated events
  - [ ] Link from Run Detail page to DVR view

- [ ] **Task 6: Create stage duration calculation** (AC: #3)
  - [ ] Utility function: calculate duration between `stage_entered` and `stage_completed` events
  - [ ] Account for QA rework cycles (multiple enter/complete pairs)
  - [ ] Display total time and rework time separately

- [ ] **Task 7: Write backend tests** (AC: #1, #4)
  - [ ] `tests/unit/application/test_list_pipeline_events_use_case.py`
  - [ ] Test: pagination (offset/limit), empty events, chronological ordering
  - [ ] `tests/integration/test_pipeline_events_endpoint.py`
  - [ ] Test: API returns paginated events with correct structure

- [ ] **Task 8: Write frontend tests** (AC: #1, #2, #3)
  - [ ] `frontend/tests/PipelineDvrTimeline.test.tsx`: renders events, stage boundaries
  - [ ] `frontend/tests/EventDetailPanel.test.tsx`: displays payload, copy button
  - [ ] `frontend/tests/stage_duration.test.ts`: duration calculation accuracy

## Dev Notes

### DVR User Journey

From the PRD Journey 2 (Time-Travel Debugger):
> A run fails. Pedro uses the React SPA Pipeline DVR to scrub back through the event history, finds an agent hallucination, updates the FastMCP constraints in the code, and resumes the run from the checkpoint directly in the UI.

This is the core debugging experience. The timeline must make it easy to:
1. See which stage failed and why
2. Inspect the exact agent output that caused the failure
3. Compare QA rework attempts
4. Understand timing (where did the pipeline spend the most time?)

### Pagination Strategy

Events are ordered by `created_at` descending (newest first) in the API, but displayed chronologically in the UI timeline. The frontend reverses the order after fetching. Pagination uses cursor-based offset for consistency.

### Performance Consideration

A full pipeline run might generate 50-100 events. Pagination with limit=50 should cover most runs in a single request. For long runs with many QA rework cycles, the "Load More" button fetches the next page.

### References

- [Source: prd.md#Observability & UI] — FR14 (time-travel debugging)
- [Source: prd.md#Measurable Outcomes] — Time to debug: <1 minute
- [Source: prd.md#User Journeys] — Journey 2: Time-Travel Debugger
- [Source: epics.md#Story 4.3] — Historical Event Scrubber
- [Source: brainstorming-session-2026-02-24.md#Theme 1] — The Pipeline DVR
