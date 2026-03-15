---
stepsCompleted: [1, 2, 3, 4, 5, 6]
workflow_completed: true
inputDocuments: 
  - _bmad-output/brainstorming/brainstorming-session-2026-02-24.md
  - _bmad-output/planning-artifacts/research/technical-Hexagonal-Architecture-Research-2026-02-24.md
date: 2026-02-24
author: Pedro
---

# Product Brief: claude_docker

## Executive Summary

The Telegram Reels Pipeline is transitioning from a fragile, terminal-bound script into a highly scalable, production-ready system. This refactor introduces an "Omni-Channel" Hexagonal Architecture powered by FastAPI and an Event Sourced MongoDB state store. By decoupling the AI agent logic from local file-system operations and exposing it to an MCP tool-driven API, the project enables real-time observability through a React SPA ("The Glass Kitchen Wall"), while simultaneously enforcing rigorous software craftsmanship standards (BDD, strict typing, double-gate validation). This ensures the project can scale across multiple client front-ends without accumulating technical debt.

---

## Core Vision

### Problem Statement

The current pipeline architecture relies heavily on unstructured code, local file-system state, and terminal-only observability. Adding new agents or maintaining existing ones is deeply painful and unpredictable, making it nearly impossible to scale or confidently add new front-end clients (like a Web UI).

### Problem Impact

Without a complete structural overhaul, the project faces imminent abandonment. The friction of debugging hallucinating agents via terminal logs, combined with the inability to cleanly decouple the Telegram presentation layer from the core pipeline, results in developer burnout and a ceiling on the product's capabilities.

### Why Existing Solutions Fall Short

Existing solutions (the current Python `PipelineRunner` and standalone `scripts/`) treat the pipeline as a closed box. They rely on the operator watching standard output in a terminal to understand what the system is doing, which is completely unscalable for a production system supporting multiple users or interfaces.

### Proposed Solution

An Event Sourced, Hexagonal API Core.
1. **The Omni-Channel Core:** FastAPI replaces the standalone runner, allowing Telegram, CI, and a React SPA to all act as decoupled clients.
2. **The Event Sourced State Machine:** MongoDB and ODMantic replace local JSON files. Every agent action is logged as an immutable event, enabling real-time SSE streaming to the frontend (The "Pipeline DVR").
3. **Strict Engineering Standards:** Introduction of Pydantic DTOs, pure frozen Domain dataclasses, `pytest-bdd` executable specs, and a strict 450-line file limit to prevent God Classes.

### Key Differentiators

From a technical perspective, this architecture is highly unique. It marries the cutting-edge **BMAD-like workflow standard** (markdown/agent-driven tasks) with a **React SPA frontend** using real-time Event Sourcing. It proves that an AI-driven pipeline can be built with the same rigorous, test-driven, Domain-Driven Design standards as a traditional enterprise backend, ensuring long-term scalability and absolute reliability.

---

## Target Users

### Primary Users: The Open Source Operators
- **Profile:** Developers, technical content creators, and hobbyists who want to run the pipeline on their own hardware (Raspberry Pi, Cloud VMs).
- **Pain Points:** When the current pipeline fails or gets stuck, there is zero visibility. They are forced to SSH into the machine and dig through terminal logs to figure out which agent hallucinated.
- **Success Vision:** A single `docker-compose up` command spins up the backend, MongoDB, and React SPA. They can trigger runs via Telegram on the go, but open the Web UI dashboard to get a rich, visual, real-time breakdown of exactly what the agents are doing via the "Pipeline DVR."

### Secondary Users: The Open Source Contributors
- **Profile:** Developers who discover the project on GitHub and want to add new agents, features, or front-ends (e.g., a Discord Bot).
- **Pain Points:** The legacy monolithic `PipelineRunner` and sloppy file-system state made it terrifying to add new features without breaking existing logic.
- **Success Vision:** They clone the repo and find a strictly enforced Hexagonal architecture. They can build a new `FastMCP` tool or add a new client by just implementing an interface, without ever touching the core pipeline logic.

### User Journey (The Operator)
1. **Discovery & Onboarding:** The user clones the GitHub repo and runs a standard `docker-compose up` which provisions the FastAPI backend, MongoDB event store, and React SPA frontend.
2. **Core Usage:** While out for a walk, the user sends a YouTube link to their configured Telegram Bot. The Telegram Bot makes a POST request to the Omni-Channel API.
3. **Observation & Debugging:** When the user gets to their computer, they open the React SPA. Because of the Event Sourced MongoDB layer, the UI instantly catches up, showing a timeline of all the steps completed so far, the exact JSON payloads the Claude agents generated, and the current active step.
4. **Success Moment:** The Reel finishes processing. The API routes the final video back to the Telegram Bot for delivery, while simultaneously displaying it in the React SPA.

---

## Success Metrics

### User Success Metrics
- **Visual Engagement:** Operators can successfully trigger a pipeline run entirely through the React SPA without needing to open a terminal or send a Telegram message.
- **Observability:** Operators can view real-time log streaming and JSON state updates for a running pipeline within the web interface.
- **Interactive Intervention:** Operators can pause the pipeline, interact with the agent (e.g., approve a script or request a change), and resume the pipeline seamlessly from the UI.
- **End-to-End Success:** The pipeline consistently produces a finalized short video matching the initial request, with all artifacts properly stored and referenced in the NoSQL database.

### Business/Project Objectives
- **Scalability of Clients:** The core pipeline successfully supports at least 3 distinct clients (Telegram, Web UI, CI) using the exact same Hexagonal API core without custom pipeline logic for each.
- **Community Adoption:** The strict adherence to clean code (BDD, Hexagonal Architecture, Double-Gate validation) makes the codebase approachable, reducing the time it takes for a new contributor to understand the flow and submit a valid PR.
- **Zero-Downtime Resilience:** If a connection drops, the UI instantly reconstructs the pipeline state upon reconnection using the MongoDB Event Store (The "Pipeline DVR").

### Key Performance Indicators (KPIs)
- **Time to Debug:** Reduce the time it takes an operator to identify why a pipeline failed from >10 minutes (SSH/grep logs) to <1 minute (visual error flag in the UI).
- **Codebase Health:** 100% of Application Use Cases have accompanying `pytest-bdd` feature files, and 0% of files exceed the 450-line limit.
- **Pipeline Reliability:** Maintain a >95% success rate for end-to-end Reel generation without unhandled internal agent crashes.

---

## MVP Scope

### Core Features
- **FastAPI / Hexagonal Core:** Complete refactor of the existing Python scripts into a unified `src/pipeline/` structure respecting strict layer boundaries and interfaces.
- **FastMCP Tool Layer:** Claude agents interacting with the system exclusively through API tools, eliminating agent-side file-system I/O for state management.
- **ODMantic MongoDB Event Store:** Immutable logging of all pipeline state changes and agent outputs into a NoSQL document database.
- **React SPA Dashboard:** A read/write "Pipeline DVR" frontend capable of streaming events via SSE, triggering new runs, and viewing logs in real-time.
- **Multi-Client Routing:** The ability to trigger and receive updates for the exact same pipeline run via either the React SPA or the legacy Telegram Bot.
- **Code Quality Enforcement:** Automated pre-commit hooks for 450-line file limits, `mypy` strict mode (no `Any`), and `pytest-bdd` executable specs for all use cases.

### Out of Scope for MVP
- **New AI Video Capabilities:** We are intentionally *not* adding new pipeline stages (like a Thumbnail Generator or new Veo3 animation features) until the core refactor is stable. The pipeline will do exactly what it does today, just under the new architecture.
- **Multi-Tenant User Accounts:** The React SPA will act as a single-tenant administrative dashboard for the operator. Full authentication/authorization schemas for multiple discrete end-users are deferred to version 2.0.

### MVP Success Criteria
- The pipeline can successfully compile a short video using the exact same prompts/tools as the old architecture, but entirely driven through the React SPA and MongoDB.
- Pull Requests containing monolithic "God Classes" or missing BDD specifications are automatically blocked by CI.

### Future Vision
- **Agent Interactivity (V2):** Allowing the operator to explicitly "pause" the pipeline from the React SPA, edit the LLM's generated content (e.g., tweaking the script), and then resume the pipeline.
- **Ecosystem Expansion:** Building a Discord Bot adapter that hooks into the Omni-Channel core as easily as the Telegram Bot does.
