"""Unit tests for the MCP server factory."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from pipeline.presentation.tools.mcp_server_factory import (
    MCP_SERVER_NAME,
    create_mcp_server,
)


def test_create_mcp_server_returns_fastmcp_instance() -> None:
    # Arrange — no setup required

    # Act
    mcp_server = create_mcp_server()

    # Assert
    assert isinstance(mcp_server, FastMCP)


def test_create_mcp_server_has_correct_name() -> None:
    # Arrange — no setup required

    # Act
    mcp_server = create_mcp_server()

    # Assert
    assert mcp_server.name == MCP_SERVER_NAME
