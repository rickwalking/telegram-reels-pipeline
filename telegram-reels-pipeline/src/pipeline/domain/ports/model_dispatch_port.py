"""ModelDispatchPort — protocol for routing prompts to specific AI models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ModelDispatchPort(Protocol):
    """Route prompts to specific AI models for QA or analysis."""

    async def dispatch(self, role: str, prompt: str, model: str | None = None) -> str: ...
