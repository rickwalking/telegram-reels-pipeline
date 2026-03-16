"""Tool registry — registers pipeline MCP tools with injected port dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from pipeline.presentation.tools.get_qa_history_tool import create_get_qa_history_tool
from pipeline.presentation.tools.get_stage_artifacts_tool import create_get_stage_artifacts_tool
from pipeline.presentation.tools.query_pipeline_status_tool import create_query_pipeline_status_tool

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort
    from pipeline.domain.ports.state_store_port import StateStorePort


@dataclass(frozen=True)
class ToolRegistryDependencies:
    """Encapsulates port dependencies required by MCP pipeline tools."""

    event_store_port: EventStorePort
    state_store_port: StateStorePort


def register_pipeline_tools(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register all pipeline tools onto the MCP server with injected dependencies.

    Tools are thin wrappers that delegate to Application Use Cases via
    the provided ports. Infrastructure adapters must never be imported here.
    """
    _register_ping_tool(mcp_server)
    _register_query_pipeline_status_tool(mcp_server, dependencies)
    _register_get_stage_artifacts_tool(mcp_server, dependencies)
    _register_get_qa_history_tool(mcp_server, dependencies)


def _register_ping_tool(mcp_server: FastMCP) -> None:
    """Register a health-check ping tool that returns 'pong'."""

    @mcp_server.tool()
    def ping() -> str:
        """Verify the MCP server is reachable and responding."""
        return "pong"


def _register_query_pipeline_status_tool(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register the query_pipeline_status tool."""
    tool_function = create_query_pipeline_status_tool(dependencies.state_store_port)
    mcp_server.tool()(tool_function)


def _register_get_stage_artifacts_tool(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register the get_stage_artifacts tool."""
    tool_function = create_get_stage_artifacts_tool(dependencies.event_store_port)
    mcp_server.tool()(tool_function)


def _register_get_qa_history_tool(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register the get_qa_history tool."""
    tool_function = create_get_qa_history_tool(dependencies.event_store_port)
    mcp_server.tool()(tool_function)
