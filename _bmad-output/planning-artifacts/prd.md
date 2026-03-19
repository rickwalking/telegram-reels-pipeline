---
stepsCompleted: [step-01-init, step-02-discovery, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
workflow_completed: true
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-instagram-reels-pipeline-2026-02-24.md
  - _bmad-output/planning-artifacts/research/technical-Hexagonal-Architecture-Research-2026-02-24.md
  - _bmad-output/brainstorming/brainstorming-session-2026-02-24.md
  - _bmad-output/planning-artifacts/prd-v1-telegram.md
  - CLAUDE.md
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 1
  projectDocs: 2
workflowType: 'prd'
classification:
  projectType: api_backend
  domain: content_creation
  complexity: medium
  projectContext: brownfield
project_name: Instagram Reels Pipeline
user_name: Pedro
date: 2026-02-24
---

# Product Requirements Document - Instagram Reels Pipeline

**Author:** Pedro
**Date:** 2026-02-24

## Executive Summary

The Telegram Reels Pipeline is transitioning from a fragile, terminal-bound script into a highly scalable, production-ready system. This refactor introduces an "Omni-Channel" Hexagonal Architecture powered by FastAPI and an Event Sourced MongoDB state store. By decoupling the AI agent logic from local file-system operations and exposing it to an MCP tool-driven API, the project enables real-time observability through a React SPA ("The Glass Kitchen Wall"). This ensures the project can scale across multiple client front-ends without accumulating technical debt.

## Success Criteria

### User Success
- **Visual Engagement:** Operators can successfully trigger a pipeline run entirely through the React SPA without needing to open a terminal or send a Telegram message.
- **Observability:** Operators can view real-time log streaming and JSON state updates for a running pipeline within the web interface.
- **Interactive Intervention:** Operators can pause the pipeline, interact with the agent (e.g., approve a script or request a change), and resume the pipeline seamlessly from the UI.
- **End-to-End Success:** The pipeline consistently produces a finalized short video matching the initial request, with all artifacts properly stored and referenced in the NoSQL database.

### Business Success
- **Scalability of Clients:** The core pipeline successfully supports at least 3 distinct clients (Telegram, Web UI, CI) using the exact same Hexagonal API core without custom pipeline logic for each.
- **Community Adoption:** The strict adherence to clean code (BDD, Hexagonal Architecture, Double-Gate validation) makes the codebase approachable, reducing the time it takes for a new contributor to understand the flow and submit a valid PR.
- **Zero-Downtime Resilience:** If a connection drops, the UI instantly reconstructs the pipeline state upon reconnection using the MongoDB Event Store (The "Pipeline DVR").

### Technical Success
- **Clean Architecture Adherence:** 100% of Domain logic relies strictly on standard library dataclasses; 100% of Application layer bounds use Protocol/DTO validation.
- **State Store Independence:** Business logic requires zero knowledge of MongoDB or ODMantic internals; all data access happens through the `StateStorePort`.
- **API Response Time:** API overhead added to agent response times must be negligible (<500ms API latency).
- **Event Sourcing Reliability:** 100% of agent state changes are committed to the Event Store before continuing pipeline execution, ensuring no "ghost states."

### Measurable Outcomes
- **Time to Debug:** Reduce the time it takes an operator to identify why a pipeline failed from >10 minutes (SSH/grep logs) to <1 minute (visual error flag in the UI).
- **Codebase Health:** 100% of Application Use Cases have accompanying `pytest-bdd` feature files, and 0% of files exceed the 450-line limit.
- **Pipeline Reliability:** Maintain a >95% success rate for end-to-end Reel generation without unhandled internal agent crashes.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy
**MVP Approach:** Problem-solving MVP. We are rebuilding the existing pipeline to be robust, scalable, and observable while maintaining the exact same video output quality.
**Resource Requirements:** Solo developer (Pedro). Leveraging existing Claude Max subscription, Raspberry Pi hardware, and existing Telegram bot.

### MVP Feature Set (Phase 1)
**Core User Journeys Supported:**
- Journey 1: Pedro — The Happy Path (Core Experience)
- Journey 2: Pedro — The Time-Travel Debugger (Error Recovery)

**Must-Have Capabilities:**
- FastAPI unified routing layer (Omni-Channel Core).
- Hexagonal Architecture (Domain, Application, Infrastructure layers).
- Pydantic DTO validation at all Application layer boundaries.
- Event Sourced state machine using MongoDB (ODMantic).
- FastMCP tool layer for Claude agent interaction.
- React SPA frontend with Server-Sent Events (SSE) for real-time monitoring.
- "Pipeline DVR" UI scrubber for time-travel debugging.
- Comprehensive BDD (`pytest-bdd`) test suite covering all use cases.

### Post-MVP Features

**Phase 2 (Growth):**
- **Journey 3: Open Source Contributor:** Building out the Discord bot adapter.
- **Agent Interactivity (V2):** Explicitly pausing the pipeline from the React SPA to edit agent outputs.

**Phase 3 (Expansion):**
- **Multi-Tenant Authentication:** Full user accounts and authorization schemas for the Web UI.
- **New AI Capabilities:** Adding entirely new agents to the pipeline (e.g., Thumbnail Generator).

### Risk Mitigation Strategy
- **Technical Risks:** Event Sourced architecture latency mitigated by using MongoDB and fully asynchronous `StateStorePort`.
- **Market Risks:** Developer burnout mitigated by front-loading BDD testing and strict typing.
- **Resource Risks:** Raspberry Pi memory limits mitigated by storing heavy binary video assets on the file system and using MongoDB only for JSON state events.

## User Journeys

### Journey 1: Pedro — The Happy Path (Core Experience)
Pedro sends a YouTube URL via Telegram and watches the pipeline progress in real-time on the React SPA dashboard via SSE. He clicks through the "Document Carousel" to see agent JSON payloads. When finished, he reviews the Reel and posts it.
**Requirements:** Telegram trigger, Web UI sync (SSE), Document Carousel, real-time updates, multi-client routing.

### Journey 2: Pedro — The Time-Travel Debugger (Error Recovery)
A run fails. Pedro uses the React SPA Pipeline DVR to scrub back through the event history, finds an agent hallucination, updates the FastMCP constraints in the code, and resumes the run from the checkpoint directly in the UI.
**Requirements:** Event Sourced state machine, MongoDB storage, Pipeline DVR scrubber, visual error surfacing, resume-from-checkpoint.

### Journey 3: The Open Source Contributor — Adding a Discord Client
Sarah clones the repo and adds a Discord bot adapter in the Infrastructure layer. Because of the strict Hexagonal Architecture and FastAPI routing, she doesn't touch the core AI logic or MongoDB event store. Her PR passes the BDD test suite automatically.
**Requirements:** Hexagonal Architecture, FastAPI routing, DTO validation, BDD testing, decoupled presentation layer.

## API Backend Specific Requirements

### Technical Architecture Considerations
- **FastAPI Foundation:** Core presentation layer providing async endpoints and OpenAPI docs.
- **Event Sourcing:** State changes recorded as immutable events in MongoDB via ODMantic.
- **Hexagonal Architecture Boundaries:** Pure Python Domain, Application Interfaces (Ports), Infrastructure implementations (Adapters).

### Endpoint Specifications
- `POST /runs`: Trigger new pipeline run.
- `GET /runs/{run_id}`: Retrieve current state.
- `GET /runs/{run_id}/events`: Retrieve event history for Pipeline DVR.

### Authentication & Data Schemas
- Simple secret token auth for MVP (single-tenant).
- Strict Pydantic DTOs for all API traffic (Double-gate validation).

### Implementation Considerations
- **SSE:** Real-time event updates to the React SPA without polling.
- **FastMCP Tooling:** Agents use FastMCP endpoints wrapping application use cases with DTO validation.

## Functional Requirements

### Trigger & Pipeline Orchestration
- **FR1:** Operators can trigger a new pipeline run via URL and optional topic (Telegram or Web UI).
- **FR2:** The system executes pipeline stages as a state machine.
- **FR3:** The system enqueues concurrent requests and processes them sequentially (FIFO).
- **FR4:** The system can pause execution for human approval or unknown layout detection.
- **FR5:** Operators can resume a paused/failed run from the last successfully completed stage.

### State Management & Event Sourcing
- **FR6:** The system records every agent action and state transition as an immutable event.
- **FR7:** The system projects the event stream into a "Run State" document.
- **FR8:** The system persists required binary media assets to the local file system.

### AI Agent Interaction
- **FR9:** AI Agents can read pipeline state via MCP tools.
- **FR10:** AI Agents can save artifacts and trigger transitions via MCP tools.
- **FR11:** The system validates agent outputs against strict DTO schemas.

### Observability & UI
- **FR12:** Operators can view active and historical runs.
- **FR13:** Operators can view real-time state changes via SSE.
- **FR14:** Operators can visually scrub through historical events (Time-Travel Debugging).
- **FR15:** Operators can inspect exact JSON payloads for completed stages.

### Core Processing Capabilities (Legacy Parity)
- **FR16:** The system downloads video, audio, and metadata from YouTube.
- **FR17:** The system analyzes transcripts for relevant moments.
- **FR18:** The system detects camera layouts and applies cropping strategies.
- **FR19:** The system generates 1080x1920 video assets using FFmpeg.
- **FR20:** The system evaluates agent outputs using automated LLM QA gates.

## Non-Functional Requirements

### Performance
- **NFR-P1:** API overhead added to agent response times must be <500ms.
- **NFR-P2:** End-to-end execution time: ≤20 min (goal), ≤45 min (acceptable).
- **NFR-P3:** FFmpeg memory usage ≤3GB peak.
- **NFR-P4:** FFmpeg CPU usage ≤80% of available cores.

### Reliability
- **NFR-R1:** Zero "ghost states"; 100% of agent state changes committed before continuing.
- **NFR-R2:** Graceful handling of unexpected shutdowns with resume capability.
- **NFR-R3:** QA rework convergence average ≤1 cycle per gate (max 3 attempts).
- **NFR-R4:** Core Domain relies strictly on standard library dataclasses.

### Scalability & Integration
- **NFR-S1:** Event Store supports high-volume writes without impacting read performance.
- **NFR-S2:** Architecture cleanly supports multiple decoupled presentation layers.
- **NFR-I1:** Agents have no direct file system I/O capabilities for state management.
- **NFR-I2:** Backend respects Telegram Bot API rate limits (30 msgs/sec global).