"""Formatter for successful MCP tool responses."""

from __future__ import annotations

import json


def format_success_response(data: dict[str, object]) -> str:
    """Serialize a successful tool result to a standard JSON string.

    Args:
        data: A dictionary of result data to include in the response payload.

    Returns:
        A JSON string with ``status`` set to ``"success"`` and the given data nested
        under the ``data`` key. Non-serializable values are coerced to strings.
    """
    return json.dumps({"status": "success", "data": data}, default=str)
