# Story 25.2: Real-Time Server-Sent Events (SSE) Integration

Status: ready-for-dev

## Story

As a System Operator,
I want the UI to automatically update as the pipeline progresses without needing to refresh,
So that I have live visibility into the exact stage the AI agents are working on.

## Acceptance Criteria

1. **Given** an active pipeline run, **When** I open the Run Detail view, **Then** the UI must establish an SSE connection to `GET /api/runs/{pipeline_run_id}/stream`, **And** stage transitions reflect within 1 second.

2. **Given** a connected SSE stream, **When** the connection drops, **Then** the client must auto-reconnect with exponential backoff, replay missed events via `Last-Event-ID`, **And** show a connection status indicator (green/amber/red).

3. **Given** a `usePipelineSse` hook, **When** an SSE event arrives, **Then** it must update the TanStack Query cache directly (`queryClient.setQueryData`), **And** the UI re-renders only the affected components.

4. **Given** the event feed component, **When** new events stream in, **Then** they must appear with a slide-in animation (honoring `prefers-reduced-motion`), **And** auto-scroll to latest unless the user has scrolled up.

## Tasks / Subtasks

- [ ] **Task 1: Create SSE backend endpoint (FastAPI)**
  - [ ] Create `src/pipeline/presentation/api/sse_stream_router.py`
  - [ ] `GET /api/runs/{pipeline_run_id}/stream` using `sse-starlette` `EventSourceResponse`
  - [ ] Subscribe to `SseBroadcastPort` for real-time events
  - [ ] Send heartbeat every 15 seconds when idle
  - [ ] Include `id` field on each event for `Last-Event-ID` reconnection
  - [ ] Register router in `application_factory.py`

- [ ] **Task 2: Create `SseConnectionService` implementation**
  - [ ] Write `sseConnection.feature` (Gherkin scenarios FIRST)
  - [ ] Implement `src/services/implementations/SseConnectionService.ts`
  - [ ] Native `EventSource` with auto-reconnect and exponential backoff
  - [ ] `Last-Event-ID` header sent on reconnection
  - [ ] Connection state tracking: `connected`, `reconnecting`, `disconnected`
  - [ ] `onEvent` callback fires for each parsed event
  - [ ] `disconnect()` cleanly closes the connection

- [ ] **Task 3: Create `usePipelineSse` app hook**
  - [ ] Write Gherkin scenarios FIRST
  - [ ] `src/app/hooks/usePipelineSse.ts`
  - [ ] Uses `useMountEffect` (not `useEffect`) to establish connection
  - [ ] Uses `useLatest` for callback to prevent stale closure
  - [ ] On event: calls `queryClient.setQueryData` to update run detail cache
  - [ ] Exposes: `connectionStatus`, `latestEventTimestamp`
  - [ ] Returns cleanup function for unmount

- [ ] **Task 4: Create `InMemorySseBroadcastAdapter` (backend)**
  - [ ] `src/pipeline/infrastructure/adapters/in_memory_sse_broadcast_adapter.py`
  - [ ] Implements `SseBroadcastPort`: `broadcast_event()`, `subscribe_to_run()`
  - [ ] `asyncio.Queue` per subscriber for fan-out
  - [ ] Clean up subscriptions on disconnect

- [ ] **Task 5: Wire event emission to SSE broadcast (backend)**
  - [ ] When `PipelineEventEmitterService` appends event to MongoDB, also call `SseBroadcastPort.broadcast_event()`
  - [ ] Non-blocking: fire-and-forget, don't block the DB write

- [ ] **Task 6: Create `ConnectionStatusIndicator` atom**
  - [ ] Write `connectionStatusIndicator.feature` (Gherkin FIRST)
  - [ ] `connectionStatusIndicatorInterface.ts` — props: `status: "connected" | "reconnecting" | "disconnected"`
  - [ ] `ConnectionStatusIndicator.tsx` — green dot / amber pulse / red dot
  - [ ] `ConnectionStatusIndicator.test.tsx` — all 3 states, `prefers-reduced-motion`
  - [ ] `ConnectionStatusIndicator.stories.tsx` — all variants + dark mode

- [ ] **Task 7: Create `EventFeed` organism**
  - [ ] Write `eventFeed.feature` (Gherkin FIRST)
  - [ ] `eventFeedInterface.ts` — props: `events`, `isLive`, `onEventClick`
  - [ ] `EventFeed.tsx` — scrolling card list, `aria-live="polite"`, auto-scroll with pause detection
  - [ ] Virtualize with `virtua` if >50 events
  - [ ] Slide-in animation on new events (transform + opacity, `prefers-reduced-motion` variant)
  - [ ] "New events — scroll to latest" button when scroll is paused
  - [ ] `EventFeed.test.tsx` + `EventFeed.stories.tsx`

- [ ] **Task 8: Backend unit + integration tests**
  - [ ] `tests/unit/presentation/test_sse_stream_router.py` — SSE endpoint sends events
  - [ ] `tests/unit/infrastructure/test_in_memory_sse_broadcast_adapter.py` — fan-out, cleanup

- [ ] **Task 9: Frontend unit tests**
  - [ ] `SseConnectionService.test.ts` — connect, reconnect, disconnect
  - [ ] `usePipelineSse.test.tsx` — cache update on event, connection status
  - [ ] `EventFeed.test.tsx` — renders events, auto-scroll, pause detection

## Dev Notes

### SSE Architecture

```
FastAPI Backend                              React Frontend
┌─────────────────────┐                     ┌──────────────────────┐
│ PipelineEventEmitter │                     │ usePipelineSse hook  │
│   ├── MongoDB append │                     │   ├── EventSource    │
│   └── SSE broadcast  │────(SSE stream)────→│   ├── queryClient    │
│                      │                     │   │   .setQueryData() │
│ SseBroadcastPort     │                     │   └── connectionState│
│   └── asyncio.Queue  │                     └──────────────────────┘
└─────────────────────┘
```

### Stale Closure Prevention

The `usePipelineSse` hook receives an `onEvent` callback that accesses TanStack Query cache. This callback MUST use `useLatest` to prevent stale closure:

```typescript
const latestOnEvent = useLatest(onEventCallback);
// In SSE handler:
sseService.onEvent((event) => latestOnEvent.current(event));
```

### References

- [Source: ux-design-specification.md#Responsive Interaction Patterns] — event feed mobile/desktop patterns
- [Source: frontend-architecture.md#Decision 2] — state management with SSE
- [Source: frontend/CLAUDE.md#State Management] — SSE hook updates query cache
