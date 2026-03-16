"""FastMCP server factory — creates and configures the MCP server for pipeline tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

MCP_SERVER_NAME = "Pipeline State Manager"
MCP_SERVER_INSTRUCTIONS = (
    "Tools for reading and writing pipeline run state. "
    "Use query_pipeline_status to check run state, "
    "save_stage_output to persist agent outputs."
)


def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server for pipeline tools."""
    mcp_server = FastMCP(
        name=MCP_SERVER_NAME,
        instructions=MCP_SERVER_INSTRUCTIONS,
    )
    return mcp_server
