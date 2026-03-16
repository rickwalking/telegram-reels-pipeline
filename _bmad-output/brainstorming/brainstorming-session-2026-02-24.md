
## Idea Organization and Prioritization

**Thematic Organization:**

**Theme 1: The Event Sourced State Machine**
_Focus: Replacing file-system JSON state with a robust, queryable data store_
- **The Hybrid State Store**: Using NoSQL for logic/metadata, retaining file system only for raw media (`ffmpeg`, `.mp4`, `.png`).
- **The Document Carousel**: An event-sourced NoSQL setup where every log/state change is an immutable document.
- **The Pipeline DVR**: A UI scrubber that allows users to time-travel through the pipeline's execution history via the event store.
- **Pattern Insight:** Decoupling the concept of "state" from "files" unlocks massive observability features.

**Theme 2: The Hexagonal API Core**
_Focus: Building a unified, heavily decoupled REST/SSE backend_
- **The Omni-Channel Core**: React SPA, Telegram Bot, and CI all use the same `CreateRunRequestDTO` to interact with the pipeline.
- **Scripts Directory Elimination**: Completely removing the `scripts/` directory as part of this refactor, replacing standalone scripts with unified entry points and API controllers.
- **The Hexagonal Tool-Adapter**: Claude writes state via MCP CLI tools that hit the REST API, keeping the AI entirely ignorant of the database.
- **The Agnostic Broadcaster**: Domain events are abstract; Infrastructure adapters map them to specific delivery mechanisms (SSE, Webhooks).
- **The Workspace Discovery Tool**: Claude uses a tool to discover paths, keeping absolute paths hidden from the UI.
- **Pattern Insight:** Extreme decoupling allows the core Use Cases to remain perfectly pure while adapting to any front-end.

**Theme 3: Extreme Code Quality Standards**
_Focus: Enforcing rigorous engineering practices during the refactor_
- **The Double-Gate Validation Matrix**: Pydantic for syntactic DTO validation + `__post_init__` for semantic Domain validation.
- **The BDD Spec Matrix**: Every Use Case must have an executable `pytest-bdd` specification using strict fixtures.
- **The File Size Limit Rule**: Pre-commit hook failing any file over 450 lines to prevent God Classes.
- **Pattern Insight:** The UI refactor is the Trojan Horse for establishing enterprise-grade codebase health.

**Prioritization Results:**

- **Top Priority Ideas:** 
  1. The Hexagonal Tool-Adapter & Omni-Channel Core (Forms the foundation of the new architecture).
  2. The Double-Gate Validation Matrix (Must be established before any new Use Cases are written).
- **Quick Win Opportunities:** 
  1. The File Size Limit Rule (Can be implemented immediately as a linting rule).
- **Breakthrough Concepts:** 
  1. The Pipeline DVR (A killer feature for the final React SPA, powered by the NoSQL event store).

**Action Planning:**

**Idea 1: Implement the Hexagonal API Core & Tool-Adapter**
**Why This Matters:** It is the backbone that allows the React SPA to exist without polluting the pipeline logic.
**Next Steps:**
1. Define the initial Pydantic DTOs (`CreateRunRequestDTO`, `RunStateResponseDTO`).
2. Build the `MongoDbStateStoreAdapter` and its Mapper class.
3. Update `prompt_builder.py` to instruct Claude to use the new local CLI API tools instead of file I/O.
4. Remove the `scripts/` directory entirely, migrating any standalone functionalities into unified API controllers or core commands.
**Resources Needed:** NestJS/FastAPI setup, MongoDB instance.
**Success Indicators:** The pipeline successfully runs via API triggers without writing JSON state files to the workspace.

**Idea 2: Establish the Code Quality Standards**
**Why This Matters:** Prevents technical debt from accumulating during the massive architectural shift.
**Next Steps:**
1. Configure `Ruff` or a pre-commit hook to enforce the 450-line file limit.
2. Draft the first Gherkin `.feature` file for a core Use Case (e.g., `start_pipeline_run.feature`).
3. Refactor one existing Domain entity (like `RunState`) to use `__post_init__` validation.
**Resources Needed:** Configuration time in CI, `pytest-bdd` setup.
**Success Indicators:** PRs automatically fail if they violate the new constraints.

## Session Summary and Insights

**Key Achievements:**
- Successfully pivoted from a "basic UI presentation layer" to a comprehensive architectural redesign using Hexagonal Architecture, Domain Driven Design, and Event Sourcing.
- Established strict coding standards to govern the implementation phase.
- Generated a clear path to decouple Claude from the database via MCP tools.

**Session Reflections:**
The use of Analogical Thinking (the restaurant kitchen) provided an excellent starting point, but the true value emerged when we applied the constraints of the Solution Matrix. By overlaying DDD principles onto the NoSQL and SSE concepts, we ensured that the new features will scale without creating spaghetti code. The decision to enforce BDD testing and file size limits ensures the resulting codebase will be as elegant as the architecture diagram.
