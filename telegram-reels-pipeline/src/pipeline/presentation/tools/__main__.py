"""Entry point for running the MCP server via stdio transport."""

from __future__ import annotations

from pipeline.presentation.tools.mcp_server_factory import create_mcp_server

if __name__ == "__main__":
    mcp_server = create_mcp_server()
    mcp_server.run(transport="stdio")
