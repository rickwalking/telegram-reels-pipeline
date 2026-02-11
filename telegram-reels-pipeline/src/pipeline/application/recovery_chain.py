"""RecoveryChain — multi-level Chain of Responsibility for error recovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, unique
from typing import TYPE_CHECKING

from pipeline.domain.errors import AgentExecutionError, PipelineError
from pipeline.domain.models import AgentRequest, AgentResult

if TYPE_CHECKING:
    from pipeline.domain.ports import AgentExecutionPort, MessagingPort

logger = logging.getLogger(__name__)


@unique
class RecoveryLevel(Enum):
    """Ordered recovery levels from least to most disruptive."""

    RETRY = "retry"
    FORK = "fork"
    FRESH = "fresh"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class RecoveryResult:
    """Outcome of a recovery attempt."""

    success: bool
    level: RecoveryLevel
    result: AgentResult | None = None
    escalation_message: str = ""


# Recovery level ordering for the chain
RECOVERY_ORDER: tuple[RecoveryLevel, ...] = (
    RecoveryLevel.RETRY,
    RecoveryLevel.FORK,
    RecoveryLevel.FRESH,
    RecoveryLevel.ESCALATE,
)


class RecoveryChain:
    """Multi-level error recovery Chain of Responsibility.

    Levels (Phase 1):
    - L1 (Retry): Re-execute the same agent with the same request
    - L2 (Fork): Re-execute with a fresh session (no session_id)
    - L3 (Fresh): Re-execute from scratch (no prior artifacts)
    - L6 (Escalate): Notify user via Telegram and pause
    """

    def __init__(
        self,
        agent_port: AgentExecutionPort,
        messaging_port: MessagingPort | None = None,
    ) -> None:
        self._agent_port = agent_port
        self._messaging_port = messaging_port

    async def recover(
        self,
        request: AgentRequest,
        error: Exception,
    ) -> RecoveryResult:
        """Attempt recovery through the chain of levels.

        Returns a RecoveryResult indicating success/failure and the level reached.
        """
        logger.warning("Recovery chain triggered for %s: %s", request.stage.value, error)

        for level in RECOVERY_ORDER:
            if level == RecoveryLevel.ESCALATE:
                return await self._escalate(request, error)

            result = await self._attempt_level(level, request)
            if result is not None:
                logger.info("Recovery succeeded at level %s for %s", level.value, request.stage.value)
                return RecoveryResult(success=True, level=level, result=result)

            logger.warning("Recovery level %s failed for %s", level.value, request.stage.value)

        # Should not reach here — escalation is always the last level
        return await self._escalate(request, error)

    async def _attempt_level(
        self,
        level: RecoveryLevel,
        request: AgentRequest,
    ) -> AgentResult | None:
        """Attempt a single recovery level. Returns AgentResult on success, None on failure."""
        try:
            if level == RecoveryLevel.RETRY:
                return await self._agent_port.execute(request)

            if level == RecoveryLevel.FORK:
                # Fork: keep prior artifacts but strip attempt history (fresh session)
                fork_request = AgentRequest(
                    stage=request.stage,
                    step_file=request.step_file,
                    agent_definition=request.agent_definition,
                    prior_artifacts=request.prior_artifacts,
                    elicitation_context=request.elicitation_context,
                )
                return await self._agent_port.execute(fork_request)

            if level == RecoveryLevel.FRESH:
                # Fresh: strip prior artifacts and attempt history
                fresh_request = AgentRequest(
                    stage=request.stage,
                    step_file=request.step_file,
                    agent_definition=request.agent_definition,
                )
                return await self._agent_port.execute(fresh_request)

        except (AgentExecutionError, PipelineError, OSError) as exc:
            logger.warning("Recovery level %s raised: %s", level.value, exc)
            return None

        return None

    async def _escalate(
        self,
        request: AgentRequest,
        error: Exception,
    ) -> RecoveryResult:
        """Escalate to the user via Telegram."""
        message = (
            f"Pipeline needs help: Stage '{request.stage.value}' failed after all recovery attempts.\n"
            f"Error: {error}\n"
            "The pipeline is paused awaiting your guidance."
        )

        if self._messaging_port is not None:
            try:
                await self._messaging_port.notify_user(message)
            except Exception:
                logger.exception("Failed to send escalation notification")

        logger.error("Recovery chain exhausted for %s — escalating", request.stage.value)
        return RecoveryResult(
            success=False,
            level=RecoveryLevel.ESCALATE,
            escalation_message=message,
        )
