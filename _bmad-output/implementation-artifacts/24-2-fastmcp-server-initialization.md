# Story 24.2: FastMCP Server Initialization

Status: ready-for-dev

## Story

As a Developer,
I want to integrate the FastMCP framework into the presentation layer,
So that the Claude Code CLI/Agent SDK has a secure server to call its designated tools.

## Acceptance Criteria

1. **Given** the pipeline environment, **When** the FastMCP server is initialized, **Then** it must expose a stdio transport for Claude Code CLI interaction, **And** it must be mountable as a sub-application within the FastAPI instance.

2. **Given** the FastMCP server is running, **When** Claude discovers available tools, **Then** it must see all registered pipeline tools with proper descriptions and parameter schemas.

3. **Given** the presentation layer architecture, **When** FastMCP tools are called, **Then** they must delegate to Application Use Cases via injected ports, **And** must NOT import from Infrastructure directly.

4. **Given** the server configuration, **When** I run `mypy --strict`, **Then** zero errors in the `presentation/tools/` package.

## Existing Code Audit

- `presentation/mcp/server.py` — EXISTS as a stub with:
  - `mcp = FastMCP("telegram-reels-agent-tools")` instance
  - `save_stage_output(payload: SaveStageDTO)` — mock, returns hardcoded string
  - `query_pipeline_status(run_id: str)` — mock, returns hardcoded string
  - No DI, no real use case invocation, no error handling
  - **`fastmcp` is NOT in pyproject.toml — non-functional**
- The server is in `presentation/mcp/` but CLAUDE.md expects `presentation/tools/` naming
- No MCP config JSON for Claude Code CLI
- No tool response formatting standard
- No tool registry pattern (tools are defined inline on the global `mcp` instance)

## Tasks / Subtasks

- [ ] **Task 1: Refactor FastMCP server** (AC: #1)
  - [ ] **[REWRITE]** Existing `presentation/mcp/server.py` is a non-functional stub with mock tools and no DI
  - [ ] Move to `src/pipeline/presentation/tools/mcp_server_factory.py` (rename `mcp/` → `tools/` per CLAUDE.md)
  - [ ] Create `create_mcp_server() -> FastMCP` factory function (replaces global `mcp` instance)
  - [ ] Configure server name: `"Pipeline State Manager"` (existing uses `"telegram-reels-agent-tools"`)
  - [ ] Set up stdio transport for Claude Code CLI
  - [ ] Set up SSE transport for potential web-based MCP clients
  - [ ] Delete old `presentation/mcp/server.py` after migration

- [ ] **Task 2: Create MCP tool registry pattern** (AC: #2, #3)
  - [ ] Create `src/pipeline/presentation/tools/tool_registry.py`
  - [ ] Define pattern for registering tools with dependency injection:
    ```python
    def register_pipeline_tools(
        mcp_server: FastMCP,
        event_store_port: EventStorePort,
        state_store_port: StateStorePort,
        file_storage_port: FileStoragePort,
    ) -> None:
    ```
  - [ ] Each tool receives ports via closure, not global state
  - [ ] Tools are thin wrappers that validate DTOs and call use cases

- [ ] **Task 3: Mount FastMCP into FastAPI** (AC: #1)
  - [ ] Update `presentation/api/application_factory.py` to mount MCP server
  - [ ] FastMCP exposes its ASGI app at `/mcp` path
  - [ ] Both REST endpoints (`/api/...`) and MCP endpoints (`/mcp/...`) coexist
  - [ ] Health check endpoint at `/mcp/health`

- [ ] **Task 4: Create MCP configuration for Claude Code** (AC: #2)
  - [ ] Create `config/mcp-pipeline.json` MCP configuration file:
    ```json
    {
      "mcpServers": {
        "pipeline": {
          "command": "poetry",
          "args": ["run", "python", "-m", "pipeline.presentation.tools.mcp_server_factory"],
          "env": {}
        }
      }
    }
    ```
  - [ ] Ensure the server can start standalone via `python -m` for stdio transport
  - [ ] Ensure it can also be mounted in FastAPI for SSE transport

- [ ] **Task 5: Create tool response formatting** (AC: #2)
  - [ ] Create `src/pipeline/presentation/tools/tool_response_formatter.py`
  - [ ] Standard success format: `{"status": "success", "data": {...}}`
  - [ ] Standard error format: `{"status": "error", "error_type": "...", "message": "..."}`
  - [ ] All tool responses use this consistent format
  - [ ] Serialize domain objects to JSON-safe dicts

- [ ] **Task 6: Write integration tests** (AC: #1, #2)
  - [ ] `tests/integration/test_mcp_server_initialization.py`
  - [ ] Test: server creates without errors
  - [ ] Test: tools are discoverable (list tools)
  - [ ] Test: stdio transport works for tool invocation
  - [ ] Use `mcp.client` for testing (official MCP test client)

- [ ] **Task 7: Write unit tests** (AC: #3, #4)
  - [ ] `tests/unit/presentation/test_tool_registry.py`: tools registered correctly
  - [ ] `tests/unit/presentation/test_tool_response_formatter.py`: format consistency
  - [ ] Verify no infrastructure imports in presentation/tools/

## Dev Notes

### FastMCP Integration Architecture

```
Claude Code CLI ──(stdio)──→ FastMCP Server ──→ Tool Function ──→ Use Case ──→ Domain
React SPA      ──(HTTP) ──→ FastAPI Router  ──→ Controller    ──→ Use Case ──→ Domain
                                ↑
                         Both share the same
                         Application Use Cases
```

The key insight: FastMCP tools and FastAPI controllers are **parallel presentation adapters**. They both call the same Application Use Cases. Neither touches Infrastructure directly.

### Dependency Injection for Tools

Since FastMCP uses decorator-based tool registration (`@mcp.tool()`), dependency injection requires a closure pattern:

```python
def register_pipeline_tools(
    mcp_server: FastMCP,
    state_store_port: StateStorePort,
) -> None:
    @mcp_server.tool()
    async def query_pipeline_status(pipeline_run_id: str) -> str:
        """Query the current state of a pipeline run."""
        use_case = GetPipelineRunDetailUseCase(state_store_port)
        result = await use_case.execute(pipeline_run_id)
        return format_tool_response(result)
```

### FastMCP Server Modes

The MCP server supports two transport modes:
1. **stdio** — for Claude Code CLI (`claude -p` with `--mcp-config`)
2. **SSE** — for web-based MCP clients (mounted in FastAPI)

Both modes share the same tool definitions and use case layer.

### References

- [Source: prd.md#Implementation Considerations] — FastMCP tooling for agent interaction
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.2] — FastMCP + FastAPI integration
- [Source: research/technical-Hexagonal-Architecture-Research-2026-02-24.md#3.3.1] — FastMCP tool snippet
- [Source: epics.md#Story 3.2] — FastMCP Server Initialization
- [Source: CLAUDE.md#Hexagonal Tool-Adapter] — Agents via MCP tools hitting REST API
