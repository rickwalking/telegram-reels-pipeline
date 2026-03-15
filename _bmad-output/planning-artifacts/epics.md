---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-create-stories, step-04-final-validation]
inputDocuments: 
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
---

# Instagram Reels Pipeline - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Instagram Reels Pipeline, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Operators can trigger a new pipeline run via URL and optional topic (Telegram or Web UI).
FR2: The system executes pipeline stages as a state machine.
FR3: The system enqueues concurrent requests and processes them sequentially (FIFO).
FR4: The system can pause execution for human approval or unknown layout detection.
FR5: Operators can resume a paused/failed run from the last successfully completed stage.
FR6: The system records every agent action and state transition as an immutable event.
FR7: The system projects the event stream into a "Run State" document.
FR8: The system persists required binary media assets to the local file system.
FR9: AI Agents can read pipeline state via MCP tools.
FR10: AI Agents can save artifacts and trigger transitions via MCP tools.
FR11: The system validates agent outputs against strict DTO schemas.
FR12: Operators can view active and historical runs.
FR13: Operators can view real-time state changes via SSE.
FR14: Operators can visually scrub through historical events (Time-Travel Debugging).
FR15: Operators can inspect exact JSON payloads for completed stages.
FR16: The system downloads video, audio, and metadata from YouTube.
FR17: The system analyzes transcripts for relevant moments.
FR18: The system detects camera layouts and applies cropping strategies.
FR19: The system generates 1080x1920 video assets using FFmpeg.
FR20: The system evaluates agent outputs using automated LLM QA gates.

### NonFunctional Requirements

NFR-P1: API overhead added to agent response times must be <500ms.
NFR-P2: End-to-end execution time: ≤20 min (goal), ≤45 min (acceptable).
NFR-P3: FFmpeg memory usage ≤3GB peak.
NFR-P4: FFmpeg CPU usage ≤80% of available cores.
NFR-R1: Zero "ghost states"; 100% of agent state changes committed before continuing.
NFR-R2: Graceful handling of unexpected shutdowns with resume capability.
NFR-R3: QA rework convergence average ≤1 cycle per gate (max 3 attempts).
NFR-R4: Core Domain relies strictly on standard library dataclasses.
NFR-S1: Event Store supports high-volume writes without impacting read performance.
NFR-S2: Architecture cleanly supports multiple decoupled presentation layers.
NFR-I1: Agents have no direct file system I/O capabilities for state management.
NFR-I2: Backend respects Telegram Bot API rate limits (30 msgs/sec global).

### Additional Requirements

- Initial setup requires manual scaffolding and Poetry to create Hexagonal layers (`domain/`, `application/`, `infrastructure/adapters`, `app/`).
- Must use standard directory structures and strict architectural boundaries.
- Python 3.11+, async/await for I/O, synchronous for pure transforms.
- Strict configurations: black (120), isort, ruff (py311, C901), mypy --strict (Any banned), pytest (asyncio_auto, 80% coverage).
- Testing follows AAA pattern, fakes over mocks, contract tests for implementations.
- Configuration loading via Pydantic BaseSettings and YAML + `.env`.
- Storage relies on file-based mechanisms (markdown, JSON, YAML) for local logic (pending NoSQL switch per latest PRD).
- System managed as a systemd daemon with specific resource constraints (MemoryMax=3G, CPUQuota=80%).
- Real-time updates delivered via SSE (Server-Sent Events) from FastAPI.
- Real-time interaction points required for FastMCP interfaces (allowing Agents to interact).

### FR Coverage Map

FR1: Epic 1 - Triggers and multi-client routing.
FR2: Epic 1 - FSM orchestration core.
FR3: Epic 1 - FIFO Queueing.
FR4: Epic 6 - Pausing for intervention.
FR5: Epic 6 - Resuming from checkpoints.
FR6: Epic 2 - Immutable event recording.
FR7: Epic 2 - State projection to document.
FR8: Epic 2 - Binary media file persistence.
FR9: Epic 3 - MCP tool reading state.
FR10: Epic 3 - MCP tool writing state.
FR11: Epic 3 - DTO validation for outputs.
FR12: Epic 4 - Historical run views.
FR13: Epic 4 - Real-time SSE updates.
FR14: Epic 4 - Time-travel DVR scrubbing.
FR15: Epic 4 - Payload inspection.
FR16: Epic 5 - YouTube download capability.
FR17: Epic 5 - Transcript analysis capability.
FR18: Epic 5 - Camera Layout detection capability.
FR19: Epic 5 - FFmpeg final processing.
FR20: Epic 5 - QA agent evaluation gates.

## Epic List

### Epic 1: Pipeline Foundation & Omni-Channel Core
**User Outcome:** Operators can trigger the pipeline from different clients (Web UI, Telegram) and the system securely manages a centralized API to accept these requests, establishing the base infrastructure for the rest of the application.
**FRs covered:** FR1, FR2, FR3

### Epic 2: The Time-Travel State Store (Event Sourcing)
**User Outcome:** Operators never lose pipeline data on crashes. The system reliably saves every state change to the NoSQL Event Store and can project current states for querying.
**FRs covered:** FR6, FR7, FR8

### Epic 3: AI Agent Core Tooling (FastMCP)
**User Outcome:** Claude Agents can securely interact with the pipeline's internal state without touching the filesystem directly, allowing them to read state and confidently save generated artifacts.
**FRs covered:** FR9, FR10, FR11

### Epic 4: Real-Time Observability Dashboard (The Glass Wall)
**User Outcome:** Operators can see exactly what the pipeline is doing at any given moment via a React SPA dashboard, inspecting JSON payloads and streaming logs via SSE.
**FRs covered:** FR12, FR13, FR14, FR15

### Epic 5: Core Processing Engine (Legacy Parity)
**User Outcome:** The pipeline successfully downloads the target video, extracts relevant transcript moments, determines framing strategy, and cuts the final Reel, all while being evaluated by automated QA.
**FRs covered:** FR16, FR17, FR18, FR19, FR20

### Epic 6: Operator Intervention & Recovery
**User Outcome:** Operators can securely pause the pipeline (for instance, when a new layout is detected), review the state via the dashboard, make manual adjustments, and resume operations smoothly.
**FRs covered:** FR4, FR5

<!-- Repeat for each epic in epics_list (N = 1, 2, 3...) -->

## Epic 1: Pipeline Foundation & Omni-Channel Core

**Goal:** Establish the foundational Hexagonal architecture, FastAPI presentation layer, and state machine orchestrator so that the pipeline can reliably receive and queue trigger requests from multiple clients (Web UI, Telegram).

### Story 1.1: Core Hexagonal Scaffolding & Poetry Setup

As a Developer,
I want to scaffold the project structure using Poetry and define the Hexagonal layer boundaries,
So that all future development adheres to strict architectural rules and dependency management.

**Acceptance Criteria:**

**Given** an empty project workspace
**When** the initial setup script is run (`poetry init` and structure creation)
**Then** the `src/pipeline` directory must contain `domain/`, `application/`, `infrastructure/adapters/`, and `app/` folders
**And** all strict configurations (black, isort, ruff, mypy --strict, pytest) must be configured in `pyproject.toml`
**And** standard library dataclasses must be the only imports allowed within the `domain/` layer.

### Story 1.2: Base Domain Models & Port Protocols

As a Developer,
I want to define the core Domain Models (e.g., `RunState`, `QueueItem`) and Port Protocols (e.g., `StateStorePort`, `MessagingPort`),
So that the application use cases can rely on stable, abstract interfaces without infrastructure coupling.

**Acceptance Criteria:**

**Given** the scaffolded Hexagonal architecture
**When** defining the core domain entities
**Then** they must be implemented as frozen standard library dataclasses (no Pydantic in `domain/`)
**And** the 8 core Port Protocols (`AgentExecutionPort`, `ModelDispatchPort`, etc.) must be defined in `domain/ports.py` using `typing.Protocol`
**And** no third-party imports (other than standard `typing`) can exist in the `domain/` layer.

### Story 1.3: FastAPI Core & Run Trigger Endpoint

As a System Operator,
I want to trigger a new pipeline run via a REST API endpoint,
So that I can programmatically start processing a YouTube URL from any external client.

**Acceptance Criteria:**

**Given** the application composition root is running
**When** a `POST /runs` request is made with a valid YouTube URL and optional topic
**Then** the request must be validated using a Pydantic DTO (e.g., `CreateRunRequestDTO`)
**And** a new `RunState` must be generated with a unique ID and `PipelineStage.ROUTER` state
**And** the response must return a `RunStateResponseDTO` containing the newly created ID within <500ms API latency.

### Story 1.4: FIFO Queue & Orchestrator Initialization

As a System Operator,
I want incoming pipeline requests to be queued and processed sequentially,
So that the system does not exceed memory or CPU constraints by running multiple heavy FFmpeg jobs concurrently.

**Acceptance Criteria:**

**Given** multiple trigger requests submitted to the API
**When** the background Orchestrator loop checks for work
**Then** it must claim the oldest pending request (FIFO) using a safe file-locking mechanism
**And** it must instantiate the `PipelineOrchestrator` to begin the FSM state execution for that specific `run_id`
**And** subsequent requests must remain queued until the active run is completed or paused.
## Epic 2: The Time-Travel State Store (Event Sourcing)

**Goal:** Implement the event-sourced persistence layer using MongoDB and ODMantic so that all pipeline state transitions and agent artifacts are immutably recorded, preventing ghost states and enabling later UI time-travel scrubbing.

### Story 2.1: ODMantic MongoDB Setup & Document Models
As a Developer,
I want to create the MongoDB connection and ODMantic Document models,
So that I can persist pipeline events and projections to a NoSQL database.

**Acceptance Criteria:**
**Given** the configured Hexagonal infrastructure layer
**When** implementing the database models
**Then** `PipelineEventDocument` must be created to store immutable state changes
**And** `RunStateDocument` must be created to hold the current projected state of a run
**And** connection string configuration must be securely loaded via Pydantic `BaseSettings`.

### Story 2.2: StateStorePort Implementation (MongoStateStore)
As a Developer,
I want to implement the `StateStorePort` using the newly created ODMantic models,
So that the core pipeline logic can save and retrieve state without coupling to MongoDB.

**Acceptance Criteria:**
**Given** the `StateStorePort` protocol defined in the domain
**When** implementing `MongoStateStore` in the infrastructure layer
**Then** it must successfully persist a `RunState` and an associated `PipelineEvent`
**And** it must successfully load an existing `RunState` by its `run_id`
**And** unit tests must verify the adapter conforms to the protocol contract.

### Story 2.3: Event-Driven State Transitions
As a System Operator,
I want every stage transition in the FSM to emit an immutable event to the database before proceeding,
So that if a crash occurs mid-stage, the exact last known state is safely recorded and the system never enters a "ghost state".

**Acceptance Criteria:**
**Given** the `PipelineOrchestrator` is processing a stage
**When** an agent successfully completes its task or an error occurs
**Then** an event (e.g., `stage_completed`, `agent_error`) must be written to MongoDB
**And** the `RunStateDocument` must be updated to reflect the new state
**And** the pipeline must not continue to the next stage until the database write is confirmed (NFR-R1).

### Story 2.4: Local File System Adapter for Binary Media
As a Developer,
I want to create a `FileStorageAdapter` for saving heavy binary assets (videos, images),
So that the MongoDB instance is kept lightweight and only handles JSON event data.

**Acceptance Criteria:**
**Given** the pipeline needs to save a downloaded video or generated thumbnail
**When** the save command is issued
**Then** the media must be written to a local `workspace/runs/{run_id}/` directory
**And** only the file path (not the binary data) should be recorded in the MongoDB Event Store
**And** file paths must use isolated directories to prevent cross-run contamination.

## Epic 3: AI Agent Core Tooling (FastMCP)

**Goal:** Provide secure, DTO-validated interfaces for AI Agents to interact with the pipeline, allowing them to read state and persist JSON/markdown artifacts without direct filesystem access.

### Story 3.1: DTO Mapping for Agent State Transfer
As a Developer,
I want to create strict Pydantic DTOs for data transitioning between the AI Agents and the Domain,
So that all incoming JSON payloads from agents are syntactically validated before reaching the Application layer.

**Acceptance Criteria:**
**Given** the need for agents to save data (e.g., transcripts, layout decisions)
**When** defining the `SaveStageDTO` and related specific output DTOs
**Then** Pydantic must strictly validate the data types and required fields
**And** Mapper functions must be created to convert these DTOs into Domain Entities safely (Double-Gate Validation).

### Story 3.2: FastMCP Server Initialization
As a Developer,
I want to integrate the `FastMCP` framework into the presentation layer,
So that the Claude code CLI/Agent SDK has a secure server to call its designated tools.

**Acceptance Criteria:**
**Given** the pipeline environment
**When** setting up the `FastMCP` server
**Then** the server must expose a stdio transport (or REST as defined by FastMCP setup)
**And** it must start seamlessly as part of the overall application lifecycle alongside FastAPI.

### Story 3.3: Read Pipeline State Tool
As an AI Agent,
I want to query the current state and prior completed stage artifacts of a pipeline run,
So that I understand my context and requirements for the current task.

**Acceptance Criteria:**
**Given** a running FastMCP server
**When** the agent calls the `query_pipeline_status(run_id)` tool
**Then** the tool must fetch the current `RunState` via the `StateStorePort`
**And** it must map the domain entity to a safe `RunStateResponseDTO`
**And** return the JSON representation back to the agent securely.

### Story 3.4: Save Stage Output Tool
As an AI Agent,
I want to save my generated artifacts directly via an MCP tool,
So that I do not have to negotiate local filesystem paths and permissions.

**Acceptance Criteria:**
**Given** a running FastMCP server
**When** the agent calls `save_stage_output(payload: SaveStageDTO)`
**Then** the server must validate the payload against the DTO schema
**And** it must use the `StateStorePort` (or event bus) to record the stage completion event and payload in MongoDB
**And** the orchestrator must acknowledge this change to trigger the next FSM transition.

## Epic 4: Real-Time Observability Dashboard (The Glass Wall)

**Goal:** Build a React Single Page Application (SPA) that acts as the "Glass Kitchen Wall", allowing operators to monitor the exact state of running pipelines via SSE, inspect JSON payloads, and view historical event streams.

### Story 4.1: React SPA Foundation & API Client
As a UI Developer,
I want to set up the base React SPA and API client,
So that I have a clean foundation to build the dashboard views.

**Acceptance Criteria:**
**Given** the React environment
**When** scaffolding the app
**Then** it must include routing for Dashboard and Run Detail views
**And** an API client must be configured to securely communicate with the FastAPI backend
**And** the UI must have a clean, modern design system applied (e.g., Tailwind CSS).

### Story 4.2: Real-time Server-Sent Events (SSE) Integration
As a System Operator,
I want the UI to automatically update as the pipeline progresses without me needing to refresh the page,
So that I have live visibility into the exact stage the AI agents are working on.

**Acceptance Criteria:**
**Given** an active pipeline run
**When** I open the Run Detail view in the SPA
**Then** the UI must establish an SSE connection to a FastAPI `GET /runs/{run_id}/stream` endpoint
**And** it must immediately reflect state changes (e.g., moving from `Transcript` to `Content` stage)
**And** it must gracefully reconnect if the connection drops.

### Story 4.3: Historical Event Scrubber (Pipeline DVR)
As a System Operator,
I want to view a timeline of all events that occurred during a specific pipeline run,
So that I can retroactively debug what happened or see exactly how long each stage took.

**Acceptance Criteria:**
**Given** a completed or failed pipeline run
**When** I navigate to its DVR view
**Then** the UI must fetch the list of events from the `GET /runs/{run_id}/events` endpoint
**And** it must render them in chronological order
**And** I must be able to click on a specific event to see its details.

### Story 4.4: Document Carousel & Payload Inspection
As a System Operator,
I want to inspect the exact JSON payloads and markdown artifacts generated by the agents at each stage,
So that I can verify the quality of their work directly from the UI.

**Acceptance Criteria:**
**Given** a pipeline run with completed stages
**When** I select a stage in the Run Detail or DVR view
**Then** the UI must display a "Document Carousel" or tabbed view
**And** it must render the JSON/markdown payload in a readable format
**And** I must be able to easily copy the payload content.

## Epic 5: Core Processing Engine (Legacy Parity)

**Goal:** Integrate the existing legacy video processing, transcript analysis, layout detection, and FFmpeg logic into the new Hexagonal architecture as encapsulated Agent Use Cases.

### Story 5.1: Video Download & Metadata Extraction Agent
As a System Operator,
I want the pipeline to download the target YouTube video and extract its metadata,
So that subsequent stages have the raw media and context needed to process the Reel.

**Acceptance Criteria:**
**Given** a valid `RunState` in the download stage
**When** the corresponding Application Use Case is executed
**Then** the `yt-dlp` tool must be invoked to download the video/audio and generate a transcript
**And** the generated assets must be stored using the `FileStorageAdapter`
**And** the state must be updated via the `StateStorePort` indicating success or failure.

### Story 5.2: Transcript Analysis & Moment Selection Agent
As an AI Agent,
I want to analyze the downloaded transcript to find the most engaging narrative moments,
So that the Reel has high-quality content focused on the requested topic.

**Acceptance Criteria:**
**Given** a downloaded transcript
**When** the Claude AI Agent processes the text
**Then** it must return a JSON payload with selected timestamps and narrative roles
**And** the payload must be validated against the required DTO
**And** a "Transcript Analyzed" event must be committed to the Event Store.

### Story 5.3: Camera Layout Detection Agent
As a System Operator,
I want the system to analyze the selected video segment and determine the optimal crop strategy,
So that the final Reel correctly frames the speakers without manual cropping.

**Acceptance Criteria:**
**Given** the selected video timestamps
**When** the Layout Detection agent runs
**Then** it must extract frames, analyze faces, and output a `LayoutDecision` JSON payload
**And** the decision must match the DTO schema and be committed to the Event Store
**And** if the layout is unknown, the agent must trigger a specific escalation state (linking to Epic 6).

### Story 5.4: FFmpeg Video Generation Agent
As a System Operator,
I want the pipeline to execute FFmpeg commands based on the layout decision,
So that the final 1080x1920 Reel is rendered correctly.

**Acceptance Criteria:**
**Given** a completed Layout Decision and source video
**When** the FFmpeg Engineer agent executes
**Then** it must run the necessary FFmpeg commands (respecting memory and CPU limits)
**And** it must generate the final `final-reel.mp4` in the run's workspace
**And** the system must commit a "Video Generated" event to the store.

### Story 5.5: Automated QA Reflection Loop
As a System Operator,
I want an automated LLM QA gate to evaluate agent outputs before moving to the next stage,
So that errors or poor choices are caught early and reworked automatically.

**Acceptance Criteria:**
**Given** an agent has produced an output (e.g., selected a transcript moment)
**When** the QA stage is triggered
**Then** a Critic model must evaluate the output against predefined criteria
**And** if it fails, the pipeline must loop back for rework (up to a configurable maximum, NFR-R3)
**And** each QA attempt must be recorded as an event in MongoDB.

## Epic 6: Operator Intervention & Recovery

**Goal:** Provide secure, controlled mechanisms for the system to pause operations, alert the operator, and allow manual resumption via the API/UI.

### Story 6.1: Escalate to Operator State Transition
As a System Operator,
I want the FSM to transition to an "Escalation" state when it encounters a critical error or an unknown layout,
So that the system does not crash or generate garbage outputs without human oversight.

**Acceptance Criteria:**
**Given** the FSM is processing a stage
**When** a predefined escalation condition is met (e.g., Layout agent returns `LayoutUnknown`)
**Then** the `PipelineOrchestrator` must set the `RunState` escalation status to active
**And** it must pause further automated transitions
**And** it must commit the paused state to MongoDB via `StateStorePort`.

### Story 6.2: Pause Pipeline API Endpoint
As a System Operator,
I want to explicitly pause a running pipeline via the REST API,
So that I can intervene if I notice the agent making a mistake in the live dashboard.

**Acceptance Criteria:**
**Given** an active pipeline run
**When** a `POST /runs/{run_id}/pause` request is made
**Then** the Orchestrator must finish its current stage (graceful pause) or halt before the next
**And** the `RunState` must be updated to a `Paused` state
**And** the UI must reflect this state immediately via SSE.

### Story 6.3: Resume Pipeline API Endpoint
As a System Operator,
I want to resume a paused pipeline run via the REST API,
So that after I have corrected an error or approved a step, the agents can continue.

**Acceptance Criteria:**
**Given** a pipeline run in a `Paused` or `Escalated` state
**When** a `POST /runs/{run_id}/resume` request is made
**Then** the Orchestrator must reload the `RunState` from MongoDB
**And** it must identify the next appropriate stage to execute based on the state machine
**And** it must resume FSM execution and update the UI via SSE.
