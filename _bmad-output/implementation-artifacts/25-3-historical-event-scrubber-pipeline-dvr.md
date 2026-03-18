# Story 25.3: Historical Event Scrubber (Pipeline DVR)

Status: ready-for-dev

## Story

As a System Operator,
I want to view a timeline of all events that occurred during a specific pipeline run,
So that I can retroactively debug what happened or see exactly how long each stage took.

## Acceptance Criteria

1. **Given** a completed or failed run, **When** I navigate to `/runs/:runId/dvr`, **Then** a chronological event timeline renders with stage boundary markers and duration labels.

2. **Given** the DVR timeline, **When** I click/tap an event marker, **Then** the detail panel shows the event's full JSON payload with syntax highlighting and copy-to-clipboard.

3. **Given** the DVR timeline, **When** I use keyboard Left/Right arrows, **Then** the selection moves between events (roving `tabindex`).

4. **Given** the events API, **When** queried with pagination, **Then** it returns events with `?offset=N&limit=M` support and the DVR loads more on scroll.

5. **Given** mobile view, **When** I tap an event, **Then** a bottom sheet slides up with the event detail (not a side panel).

## Tasks / Subtasks

- [ ] **Task 1: Create events list API endpoint (backend)**
  - [ ] `GET /api/runs/{pipeline_run_id}/events` with `offset`/`limit` query params
  - [ ] `PipelineEventListResponseDTO` with pagination metadata
  - [ ] `PipelineEventItemDTO`: `event_id`, `event_type`, `stage_name`, `created_at`, `payload_summary`
  - [ ] Ordered by `created_at` ascending (chronological)

- [ ] **Task 2: Create event detail API endpoint (backend)**
  - [ ] `GET /api/runs/{pipeline_run_id}/events/{event_id}`
  - [ ] Returns full event payload
  - [ ] 404 if event not found

- [ ] **Task 3: Create `TimelineEventMarker` atom**
  - [ ] Write `timelineEventMarker.feature` (Gherkin FIRST)
  - [ ] `timelineEventMarkerInterface.ts` — props: `eventType`, `stageName`, `timestamp`, `isSelected`, `onClick`
  - [ ] `TimelineEventMarker.tsx` — `<button>` element, min 44x44px touch target, `aria-label` with event description
  - [ ] Color-coded by event type: stage events (blue), QA events (amber), errors (red)
  - [ ] `TimelineEventMarker.test.tsx` + `.stories.tsx`

- [ ] **Task 4: Create `StageBoundaryMarker` atom**
  - [ ] `stageBoundaryMarkerInterface.ts` — props: `stageName`, `durationSeconds`
  - [ ] `StageBoundaryMarker.tsx` — decorative divider (`aria-hidden="true"`), duration label with `tabular-nums`
  - [ ] `<time datetime="PTNs">` for semantic correctness
  - [ ] Test + story

- [ ] **Task 5: Create `EventDetailPanel` molecule**
  - [ ] Write `eventDetailPanel.feature` (Gherkin FIRST)
  - [ ] `eventDetailPanelInterface.ts` — props: `event`, `onClose`
  - [ ] JSON payload with syntax highlighting (dark-mode aware)
  - [ ] Collapsible sections (`<button>` with `aria-expanded`)
  - [ ] CopyButton for full payload
  - [ ] Renders as side panel (desktop) or bottom sheet via `ModalSheetLayout` (mobile)
  - [ ] Tests + stories

- [ ] **Task 6: Create `PipelineDvrTimeline` organism**
  - [ ] Write `pipelineDvrTimeline.feature` (Gherkin FIRST)
  - [ ] `pipelineDvrTimelineInterface.ts` — props: `runId`, `selectedEventId`, `onEventSelect`
  - [ ] Fetches events via `useSuspenseQuery` + `<Suspense>` boundary with skeleton
  - [ ] Renders `TimelineEventMarker` + `StageBoundaryMarker` components
  - [ ] Keyboard navigation: Left/Right arrows (roving `tabindex`)
  - [ ] URL state: selected event synced via nuqs `?event=evt-123`
  - [ ] Virtualize if >50 events (`content-visibility: auto`)
  - [ ] `touch-action: pan-y` (mobile vertical), `overscroll-behavior: contain`
  - [ ] Timestamps use `Intl.DateTimeFormat`
  - [ ] Tests + stories

- [ ] **Task 7: Create `PipelineDvrPage` page**
  - [ ] `src/app/pages/PipelineDvrPage/PipelineDvrPage.tsx`
  - [ ] Layout: `DvrLayout` template — resizable split (desktop) / stacked (mobile)
  - [ ] Left/top: `PipelineDvrTimeline`
  - [ ] Right/bottom: `EventDetailPanel`
  - [ ] Back link to run detail: `<Link to="/runs/$runId">`
  - [ ] Stage duration summary bar at top

- [ ] **Task 8: Create `JsonPayloadViewer` molecule**
  - [ ] Write Gherkin scenarios FIRST
  - [ ] `jsonPayloadViewerInterface.ts` — props: `payload`, `maxHeight?`
  - [ ] Syntax highlighting via CSS (no heavy dependency)
  - [ ] Collapsible object/array sections
  - [ ] `break-words` / `overflow-wrap` for long values
  - [ ] Dark-mode aware theme
  - [ ] `content-visibility: auto` on large JSON trees
  - [ ] CopyButton integrated
  - [ ] Tests + stories

- [ ] **Task 9: Write E2E tests**
  - [ ] `e2e/features/pipeline-dvr.feature`:
    - Scenario: Navigate to DVR from run detail
    - Scenario: Click event to see detail
    - Scenario: Keyboard navigate between events
    - Scenario: Copy event payload
  - [ ] Playwright MCP step definitions

## Dev Notes

### DVR User Journey (from UX spec)

```
[Dashboard] → See red "Failed" badge → tap
[Run Detail] → Stage stepper shows red on "transcript" → tap "View DVR"
[DVR Timeline] → Scrub through events → tap error event (red marker)
[Event Detail] → See exact error + QA history → "Found it!" moment
```

Time to debug target: **< 1 minute** (PRD measurable outcome).

### Mobile vs Desktop Layout

| Element | Desktop | Mobile |
|---------|---------|--------|
| Timeline | Left panel (resizable) | Full width, vertical scroll |
| Event detail | Right panel (resizable) | Bottom sheet (slide up) |
| Navigation | Mouse click + keyboard arrows | Tap + swipe |
| Payload view | Full syntax-highlighted panel | Collapsible accordion |

### References

- [Source: ux-design-specification.md#Screen 3: Pipeline DVR] — wireframe and interaction patterns
- [Source: ux-design-specification.md#Journey 2: Time-Travel Debugger] — user journey flow
- [Source: frontend-architecture.md#Decision 4] — API client with Zod validation
- [Source: frontend/CLAUDE.md#Accessibility] — keyboard nav, touch targets, aria patterns
