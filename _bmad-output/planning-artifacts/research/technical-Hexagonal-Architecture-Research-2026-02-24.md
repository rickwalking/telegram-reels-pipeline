# Technical Research Document

**Type:** Technical
**Topic:** Implementation patterns for MongoDB Mongoose-equivalents in Python, MCP Servers in Flask, and Architectural Snippets for Event-Sourced Hexagonal Pipeline
**Goals:** Define structured models for MongoDB, create concrete code snippets for architecture decisions (DTOs, Mappers, Adapters), research MCP Server implementation via Flask, and validate findings using CLink consensus.
**Date:** 2026-02-24

## 1. Executive Summary
This research validates the architectural decisions made during the brainstorming session regarding the migration to a Hexagonal API Core backed by a NoSQL Event Store. 
- **MongoDB ODM**: `ODMantic` and `Pygoose` emerged as the best Python equivalents to Mongoose, natively supporting Pydantic validation which perfectly aligns with our Presentation Layer DTO strategy.
- **MCP Server**: The `FastMCP` framework is the industry standard for exposing Python functions as Model Context Protocol tools. It can run atop standard ASGI servers (like FastAPI), eliminating the need for raw Flask boilerplate while keeping Claude perfectly decoupled from the database.
- **Hexagonal Integrity**: We have drafted specific Python snippets demonstrating how `FastMCP` tools map to Pydantic DTOs, pass through pure Domain dataclasses (with double-gate validation), and persist via an `ODMantic` Repository Adapter.

## 3. Findings

### 3.1 Python Mongoose Equivalents for MongoDB
The Python ecosystem in 2026 relies heavily on Pydantic for validation. The top Mongoose equivalents that support AsyncIO and Pydantic natively are:
1. **ODMantic**: Built on Pydantic v2.5+. Supports both sync and async operations. It integrates natively with FastAPI/ASGI frameworks. It is highly mature.
2. **Pygoose**: Specifically inspired by Mongoose ergonomics. Includes a fluent `QuerySet` API, lifecycle hooks, and built-in plugins for timestamps.

**Recommendation:** Use `ODMantic` for the Infrastructure Repository Adapter since it provides the cleanest mapping between our Presentation DTOs (Pydantic) and our MongoDB Document layer without imposing heavy ORM magic on our pure Domain models.

### 3.2 Building MCP Servers with FastAPI
Instead of manually wiring JSON-RPC over HTTP using generic ASGI, the modern 2026 approach is to use the official **FastMCP** framework (`from mcp.server.fastmcp import FastMCP`), which integrates natively with FastAPI.
- FastMCP uses simple decorators (`@mcp.tool()`) to instantly expose Python functions to Claude Code.
- It handles all JSON-RPC negotiation and Pydantic auto-validation for tool arguments.
- FastMCP can be mounted directly into a FastAPI application as a sub-app or router, allowing both standard REST endpoints (for the React SPA frontend) and MCP endpoints (for Claude) to live side-by-side in the same `FastAPI()` instance.

### 3.3 Architectural Snippets (Hexagonal + Event Sourcing + FastAPI)

#### 1. The Expected Folder Structure
With the deprecation of the `scripts/` directory, the refactored architecture enforces strict Hexagonal boundaries and explicitly separates the Presentation layer (FastAPI controllers/tools).

```text
src/pipeline/
├── app/                  # Application bootstrap and FastAPI wiring
│   ├── main.py           # FastAPI() app creation and router inclusion
│   └── settings.py       # Pydantic BaseSettings for the whole app
├── domain/               # Core business rules (NO DEPENDENCIES)
│   ├── models/           # Pure frozen dataclasses (RunState, Event)
│   ├── events/           # Domain event definitions
│   ├── errors/           # Custom exception classes
│   └── ports.py          # Abstract Base Classes (StateStorePort, EventBusPort)
├── application/          # Orchestration and Use Cases (Depends on Domain only)
│   ├── use_cases/        # start_run.py, handle_stage.py
│   └── services/         # Orchestrator classes
├── presentation/         # Incoming boundaries (FastAPI, FastMCP)
│   ├── api/              # FastAPI routers for React SPA (e.g., /api/runs)
│   ├── tools/            # FastMCP tools for Claude (e.g., save_stage_output)
│   └── dtos/             # Pydantic models for incoming requests/responses
└── infrastructure/       # Outgoing boundaries (Adapters)
    ├── database/         # ODMantic implementations (MongoDbStateStoreAdapter)
    ├── event_bus/        # Implementations for SSE / Event Broadcasting
    ├── ai/               # Adapters to interact with LLMs (if needed)
    └── mappers/          # Translates Domain models to/from Infrastructure models
```

#### 2. The FastMCP Tool (Presentation Layer Edge in FastAPI)
This is what Claude calls. It acts as the entry point, leveraging FastAPI underneath.
```python
from mcp.server.fastmcp import FastMCP
from pipeline.application.use_cases import save_stage_use_case
from pipeline.presentation.dtos import SaveStageDTO

mcp = FastMCP("Pipeline State Manager")

@mcp.tool()
async def save_stage_output(run_id: str, stage: str, payload_json: str) -> str:
    """Claude uses this tool to save JSON state instead of writing to disk."""
    # 1. Syntactic Validation (Pydantic DTO)
    dto = SaveStageDTO.model_validate_json(payload_json)
    
    # 2. Pass to Application Use Case
    result = await save_stage_use_case(run_id, stage, dto)
    return f"Success: {result.status}"
```

#### 3. The Front-End Event Storing (Event Sourcing)
Every action taken by Claude or the UI generates an event stored in MongoDB. This enables the "Pipeline DVR" and guaranteed SSE delivery for the React SPA.
```python
# infrastructure/database/models.py
from odmantic import Model
from datetime import datetime

class PipelineEventDoc(Model):
    run_id: str
    event_type: str
    payload: dict
    timestamp: datetime

# application/use_cases/save_stage_use_case.py
async def save_stage_use_case(run_id: str, stage: str, dto: SaveStageDTO, event_store: EventStorePort):
    # Process logic...
    
    # Create Event Sourcing record
    event = DomainEvent(run_id=run_id, event_type=f"stage_completed:{stage}", payload=dto.model_dump())
    
    # Store event (NoSQL Document Carousel)
    await event_store.append(event)
    
    # The EventStoreAdapter will automatically trigger pg_notify/SSE broadcast after appending
```

#### 2. The Domain Entity (Double-Gate Validation)
Pure Python. No external dependencies.
```python
from dataclasses import dataclass
from pipeline.domain.errors import DomainValidationError

@dataclass(frozen=True)
class RunState:
    run_id: str
    youtube_url: str
    current_stage: str
    
    def __post_init__(self):
        # 3. Semantic / Business Validation
        if not self.youtube_url.startswith("https://"):
            raise DomainValidationError("Invalid YouTube URL in Domain.")
        if len(self.run_id) < 8:
            raise DomainValidationError("Run ID must be secure.")
```

#### 3. The Infrastructure Adapter (ODMantic)
Implements the port defined by the Application layer.
```python
from pipeline.domain.ports import StateStorePort
from pipeline.domain.models import RunState
from odmantic import AIOEngine, Model

# Mongo Document Definition
class RunStateDoc(Model):
    run_id: str
    youtube_url: str
    current_stage: str

class MongoDbStateStoreAdapter(StateStorePort):
    def __init__(self, engine: AIOEngine):
        self.engine = engine
        
    async def save(self, state: RunState) -> None:
        # Mapper: Domain -> MongoDoc
        doc = RunStateDoc(
            run_id=state.run_id,
            youtube_url=state.youtube_url,
            current_stage=state.current_stage
        )
        await self.engine.save(doc)
```

## 4. CLink Validation & Consensus
Based on an evaluation of the Python Hexagonal Architecture snippets against the project rules, the consensus is **Yes**.

**Reasoning:**
- **Dependency Inversion Principle:** The Application Use Case does not import `ODMantic` or `MongoDB` directly. It relies on the `StateStorePort`. The Infrastructure layer (`MongoDbStateStoreAdapter`) implements this port.
- **Double-Gate Validation:** The `FastMCP` tool validates the incoming payload syntactically using a Pydantic DTO. The Domain Entity (`RunState`) validates the business rules natively in its `__post_init__` without any external dependencies.
- **Clean Layering:** The tool (Presentation) knows about the Use Case. The Use Case knows about the Domain. The Adapter (Infrastructure) knows about the Domain and ODMantic. No layer reaches outwards inappropriately.

## 5. Next Steps & Recommendations
1. **Adopt ODMantic:** It seamlessly bridges the gap between Pydantic DTOs and MongoDB while allowing pure frozen dataclasses to remain independent in the Domain layer.
2. **Implement FastMCP:** Migrate from standard Flask/FastAPI REST endpoints to `FastMCP`. This dramatically simplifies how Claude interacts with the system, turning file I/O operations into direct function calls.
3. **Draft the DTO Layer:** Create `src/pipeline/presentation/dtos.py` to hold the Pydantic models required for the FastMCP tool validation.
4. **Draft the Repositories:** Create `src/pipeline/infrastructure/adapters/mongodb_state_store.py` implementing the `StateStorePort` using ODMantic `AIOEngine`.
