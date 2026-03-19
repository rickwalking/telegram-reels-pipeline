"""Tool registry — registers pipeline MCP tools with injected port dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from pipeline.presentation.tools.save_stage_output_tool import register_save_stage_output_tool

if TYPE_CHECKING:
    from pipeline.domain.ports.event_store_port import EventStorePort
    from pipeline.domain.ports.file_storage_port import FileStoragePort
    from pipeline.domain.ports.state_store_port import StateStorePort


@dataclass(frozen=True)
class ToolRegistryDependencies:
    """Encapsulates port dependencies required by MCP pipeline tools."""

    event_store_port: EventStorePort
    state_store_port: StateStorePort
    file_storage_port: FileStoragePort


def register_pipeline_tools(
    mcp_server: FastMCP,
    dependencies: ToolRegistryDependencies,
) -> None:
    """Register all pipeline tools onto the MCP server with injected dependencies.

    Tools are thin wrappers that delegate to Application Use Cases via
    the provided ports. Infrastructure adapters must never be imported here.
    """
    _register_ping_tool(mcp_server)
    register_save_stage_output_tool(mcp_server, dependencies)


def _register_ping_tool(mcp_server: FastMCP) -> None:
    """Register a health-check ping tool that returns 'pong'."""

    @mcp_server.tool()
    def ping() -> str:
        """Verify the MCP server is reachable and responding."""
        return "pong"
