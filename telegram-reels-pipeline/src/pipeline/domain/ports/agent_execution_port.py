"""AgentExecutionPort — protocol for executing BMAD agents via CLI or SDK backend."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pipeline.domain.models import AgentRequest, AgentResult


@runtime_checkable
class AgentExecutionPort(Protocol):
    """Execute a BMAD agent via CLI or SDK backend."""

    async def execute(self, request: AgentRequest) -> AgentResult: ...
