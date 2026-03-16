# Story 25.2: Real-Time Server-Sent Events (SSE) Integration

Status: ready-for-dev

## Story

As a System Operator,
I want the UI to automatically update as the pipeline progresses without needing to refresh,
So that I have live visibility into the exact stage the AI agents are working on.

## Acceptance Criteria

1. **Given** an active pipeline run, **When** I open the Run Detail view, **Then** the UI must establish an SSE connection to `GET /api/runs/{pipeline_run_id}/stream`, **And** immediately reflect state changes (e.g., stage transitions, QA results).

2. **Given** a connected SSE stream, **When** a pipeline event occurs, **Then** the UI must update within 1 second of the event being persisted to MongoDB.

3. **Given** a dropped SSE connection, **When** the network recovers, **Then** the client must automatically reconnect and replay missed events.

4. **Given** no active pipeline run, **When** the SSE stream is idle, **Then** the server must send periodic heartbeat messages to keep the connection alive.

## Tasks / Subtasks

- [ ] **Task 1: Create SSE FastAPI endpoint** (AC: #1, #2, #4)
  - [ ] Create `src/pipeline/presentation/api/sse_stream_router.py`
  - [ ] `GET /api/runs/{pipeline_run_id}/stream` endpoint
  - [ ] Use `sse-starlette` `EventSourceResponse` for SSE delivery
  - [ ] Subscribe to `SseBroadcastPort` for real-time events
  - [ ] Send heartbeat every 15 seconds when idle
  - [ ] Include `Last-Event-ID` support for reconnection

- [ ] **Task 2: Implement SseBroadcastPort adapter** (AC: #2)
  - [ ] Create `src/pipeline/infrastructure/adapters/in_memory_sse_broadcast_adapter.py`
  - [ ] `InMemorySseBroadcastAdapter` implementing `SseBroadcastPort`:
    - `async broadcast_event(pipeline_run_id: str, event: PipelineStateEvent) -> None`
    - `async subscribe_to_run(pipeline_run_id: str) -> AsyncIterator[PipelineStateEvent]`
  - [ ] Use `asyncio.Queue` per subscriber for fan-out delivery
  - [ ] Clean up subscriptions on disconnect

- [ ] **Task 3: Wire event emission to SSE broadcast** (AC: #2)
  - [ ] When `PipelineEventEmitterService` appends an event to MongoDB, also broadcast via `SseBroadcastPort`
  - [ ] This bridges the persistent store and real-time delivery
  - [ ] Pattern: append to DB → broadcast to SSE subscribers (fire-and-forget, non-blocking)

- [ ] **Task 4: Create React SSE hook** (AC: #1, #3)
  - [ ] Create `frontend/src/hooks/use_pipeline_sse.ts`
  - [ ] Custom React hook: `usePipelineSse(pipelineRunId: string)`
  - [ ] Returns: `{ events: PipelineEvent[], connectionStatus: string, latestStage: string }`
  - [ ] Use native `EventSource` API
  - [ ] Auto-reconnect with exponential backoff on connection loss
  - [ ] Track `Last-Event-ID` for replay on reconnect

- [ ] **Task 5: Integrate SSE into Run Detail page** (AC: #1)
  - [ ] Update `RunDetailPage.tsx` to use `usePipelineSse` hook
  - [ ] Real-time updates to: current stage indicator, status badge, event log
  - [ ] Visual pulse/animation when a new event arrives
  - [ ] Connection status indicator (connected/reconnecting/disconnected)

- [ ] **Task 6: Create SSE event type formatting** (AC: #1, #2)
  - [ ] Define SSE event types: `stage_update`, `qa_result`, `error`, `heartbeat`
  - [ ] Each event type has a specific JSON payload structure
  - [ ] Frontend dispatches on event type to update appropriate UI sections

- [ ] **Task 7: Write integration tests** (AC: #1, #2, #3)
  - [ ] `tests/integration/test_sse_stream_endpoint.py`
  - [ ] Test: connect → emit event → receive via SSE
  - [ ] Test: reconnect with Last-Event-ID → receive missed events
  - [ ] Test: heartbeat sent during idle
  - [ ] Use `httpx` SSE client for testing

- [ ] **Task 8: Write frontend tests** (AC: #1, #3)
  - [ ] `frontend/tests/use_pipeline_sse.test.ts`
  - [ ] Test: hook connects and receives events
  - [ ] Test: auto-reconnect on disconnect
  - [ ] Mock EventSource for unit testing

## Dev Notes

### SSE vs WebSocket

SSE was chosen over WebSocket because:
- Simpler server implementation (uni-directional)
- Native browser `EventSource` API with auto-reconnect
- Works through HTTP proxies without upgrade negotiation
- Sufficient for our read-only real-time use case

### Event Fan-Out Architecture

```
PipelineEventEmitterService
    ├── EventStorePort.append_event() ──→ MongoDB (persistent)
    └── SseBroadcastPort.broadcast() ──→ In-Memory Queue ──→ SSE Subscribers
                                                               ├── Browser 1
                                                               └── Browser 2
```

### Reconnection with Replay

Each SSE event includes an `id` field (the event's `event_id`). When a client reconnects, it sends `Last-Event-ID` header. The server queries MongoDB for events after that ID and replays them before resuming the live stream.

### NFR Compliance

- NFR-S1: Event store supports high-volume writes — SSE broadcast is non-blocking, decoupled from DB writes
- Zero-Downtime Resilience: UI reconstructs state on reconnection via event replay

### References

- [Source: prd.md#Observability & UI] — FR13 (real-time SSE updates)
- [Source: prd.md#Business Success] — Zero-downtime resilience, Pipeline DVR
- [Source: epics.md#Story 4.2] — Real-time SSE Integration
- [Source: brainstorming-session-2026-02-24.md#Theme 2] — The Agnostic Broadcaster
