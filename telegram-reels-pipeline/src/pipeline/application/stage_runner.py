"""StageRunner — orchestrates a single stage through execute -> QA -> recovery."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.domain.models import AgentRequest, PipelineEvent, ReflectionResult
from pipeline.domain.types import GateName

if TYPE_CHECKING:
    from pipeline.application.event_bus import EventBus
    from pipeline.application.recovery_chain import RecoveryChain
    from pipeline.application.reflection_loop import ReflectionLoop

logger = logging.getLogger(__name__)


class StageRunner:
    """Run a single pipeline stage through the full execute -> QA -> recovery cycle.

    Coordinates:
    - QA evaluation via ReflectionLoop
    - Error recovery via RecoveryChain
    - Event emission via EventBus

    State machine transitions are handled by the caller.
    """

    def __init__(
        self,
        reflection_loop: ReflectionLoop,
        recovery_chain: RecoveryChain,
        event_bus: EventBus,
    ) -> None:
        self._reflection_loop = reflection_loop
        self._recovery_chain = recovery_chain
        self._event_bus = event_bus

    async def run_stage(
        self,
        request: AgentRequest,
        gate: GateName,
        gate_criteria: str,
    ) -> ReflectionResult:
        """Execute a stage through the reflection loop with recovery on failure.

        Args:
            request: The agent request to execute.
            gate: Name of the QA gate for evaluation.
            gate_criteria: Criteria text for the QA evaluation.

        Emits events for stage entry and completion/failure.
        Returns the ReflectionResult from the QA loop.
        Raises on unrecoverable failure.
        """
        stage = request.stage
        logger.info("Starting stage: %s", stage.value)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="pipeline.stage_entered",
                stage=stage,
            )
        )

        try:
            result = await self._reflection_loop.run(request, gate, gate_criteria)
        except Exception as exc:
            logger.error("Stage %s failed: %s", stage.value, exc)
            try:
                recovery_result = await self._recovery_chain.recover(request, exc)
                logger.info(
                    "Recovery succeeded for stage %s at level %s",
                    stage.value,
                    recovery_result.level.value,
                )
                result = await self._reflection_loop.run(request, gate, gate_criteria)
            except Exception as recovery_exc:
                logger.error("Recovery failed for stage %s: %s", stage.value, recovery_exc)
                await self._event_bus.publish(
                    PipelineEvent(
                        timestamp=datetime.now(UTC).isoformat(),
                        event_name="pipeline.run_failed",
                        stage=stage,
                        data={"reason": str(recovery_exc)},
                    )
                )
                raise recovery_exc from exc

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="pipeline.stage_completed",
                stage=stage,
                data={
                    "score": result.best_critique.score,
                    "decision": result.best_critique.decision.value,
                },
            )
        )

        logger.info(
            "Stage %s completed: %s (score=%d)",
            stage.value,
            result.best_critique.decision.value,
            result.best_critique.score,
        )
        return result
