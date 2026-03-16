"""Formatter for error MCP tool responses."""

from __future__ import annotations

import json


def format_error_response(error_type: str, message: str) -> str:
    """Serialize an error result to a standard JSON string.

    Args:
        error_type: A short machine-readable identifier for the error category
            (e.g. ``"not_found"``, ``"validation_error"``).
        message: A human-readable description of what went wrong.

    Returns:
        A JSON string with ``status`` set to ``"error"`` and the given
        ``error_type`` and ``message`` fields included.
    """
    return json.dumps({"status": "error", "error_type": error_type, "message": message})
