"""PipelineRunner — drive a full pipeline run through all 8 stages."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.models import AgentRequest, PipelineEvent, QueueItem, RunState
from pipeline.domain.types import GateName, RunId

if TYPE_CHECKING:
    from pipeline.application.delivery_handler import DeliveryHandler
    from pipeline.application.event_bus import EventBus
    from pipeline.application.stage_runner import StageRunner
    from pipeline.domain.ports import StateStorePort

logger = logging.getLogger(__name__)

# Ordered stage sequence matching BMAD workflow
_STAGE_SEQUENCE: tuple[PipelineStage, ...] = (
    PipelineStage.ROUTER,
    PipelineStage.RESEARCH,
    PipelineStage.TRANSCRIPT,
    PipelineStage.CONTENT,
    PipelineStage.LAYOUT_DETECTIVE,
    PipelineStage.FFMPEG_ENGINEER,
    PipelineStage.ASSEMBLY,
    PipelineStage.DELIVERY,
)

# Maps pipeline stage to (step_file_name, agent_directory, gate_name)
_STAGE_DISPATCH: dict[PipelineStage, tuple[str, str, str]] = {
    PipelineStage.ROUTER: ("stage-01-router.md", "router", "router"),
    PipelineStage.RESEARCH: ("stage-02-research.md", "research", "research"),
    PipelineStage.TRANSCRIPT: ("stage-03-transcript.md", "transcript", "transcript"),
    PipelineStage.CONTENT: ("stage-04-content.md", "content-creator", "content"),
    PipelineStage.LAYOUT_DETECTIVE: ("stage-05-layout-detective.md", "layout-detective", "layout"),
    PipelineStage.FFMPEG_ENGINEER: ("stage-06-ffmpeg-engineer.md", "ffmpeg-engineer", "ffmpeg"),
    PipelineStage.ASSEMBLY: ("stage-07-assembly.md", "qa", "assembly"),
    PipelineStage.DELIVERY: ("stage-08-delivery.md", "delivery", ""),
}


def _generate_run_id() -> RunId:
    """Generate a collision-resistant run ID with microseconds and random suffix."""
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    suffix = os.urandom(2).hex()
    return RunId(f"{ts}-{suffix}")


class PipelineRunner:
    """Drive a complete pipeline run through all stages.

    Coordinates StageRunner, EventBus, StateStore, and DeliveryHandler
    to execute the full BMAD workflow.
    """

    def __init__(
        self,
        stage_runner: StageRunner,
        state_store: StateStorePort,
        event_bus: EventBus,
        delivery_handler: DeliveryHandler | None,
        workflows_dir: Path,
    ) -> None:
        self._stage_runner = stage_runner
        self._state_store = state_store
        self._event_bus = event_bus
        self._delivery_handler = delivery_handler
        self._workflows_dir = workflows_dir

    async def run(self, item: QueueItem, workspace: Path) -> RunState:
        """Execute a full pipeline run for a queue item.

        Creates initial RunState, drives through all stages in sequence,
        and delivers the final output. Returns the final RunState.
        """
        run_id = _generate_run_id()
        now = datetime.now(UTC).isoformat()

        state = RunState(
            run_id=run_id,
            youtube_url=item.url,
            current_stage=_STAGE_SEQUENCE[0],
            current_attempt=1,
            qa_status=QAStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        await self._state_store.save_state(state)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=now,
                event_name="pipeline.run_started",
                data={"run_id": run_id, "url": item.url},
            )
        )

        artifacts: tuple[Path, ...] = ()
        for stage in _STAGE_SEQUENCE:
            state = RunState(
                run_id=state.run_id,
                youtube_url=state.youtube_url,
                current_stage=stage,
                current_attempt=1,
                qa_status=QAStatus.PENDING,
                stages_completed=state.stages_completed,
                escalation_state=state.escalation_state,
                created_at=state.created_at,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await self._state_store.save_state(state)

            _, _, gate_name = _STAGE_DISPATCH[stage]

            if gate_name:
                request = self._build_request(stage, workspace, artifacts, item)
                result = await self._stage_runner.run_stage(
                    request,
                    gate=GateName(gate_name),
                    gate_criteria=await self._load_gate_criteria(gate_name),
                )
                artifacts = result.artifacts

                if result.escalation_needed:
                    state = RunState(
                        run_id=state.run_id,
                        youtube_url=state.youtube_url,
                        current_stage=stage,
                        current_attempt=state.current_attempt,
                        qa_status=QAStatus.FAILED,
                        stages_completed=state.stages_completed,
                        escalation_state=EscalationState.QA_EXHAUSTED,
                        created_at=state.created_at,
                        updated_at=datetime.now(UTC).isoformat(),
                    )
                    await self._state_store.save_state(state)
                    logger.warning("Pipeline paused at %s — escalation needed", stage.value)
                    return state
            elif stage == PipelineStage.DELIVERY and self._delivery_handler is not None:
                await self._execute_delivery(artifacts, workspace)

            # Mark stage as completed
            state = RunState(
                run_id=state.run_id,
                youtube_url=state.youtube_url,
                current_stage=stage,
                current_attempt=1,
                qa_status=QAStatus.PASSED,
                stages_completed=(*state.stages_completed, stage.value),
                escalation_state=EscalationState.NONE,
                created_at=state.created_at,
                updated_at=datetime.now(UTC).isoformat(),
            )
            await self._state_store.save_state(state)

        # Final state
        state = RunState(
            run_id=state.run_id,
            youtube_url=state.youtube_url,
            current_stage=PipelineStage.COMPLETED,
            current_attempt=1,
            qa_status=QAStatus.PASSED,
            stages_completed=state.stages_completed,
            escalation_state=EscalationState.NONE,
            created_at=state.created_at,
            updated_at=datetime.now(UTC).isoformat(),
        )
        await self._state_store.save_state(state)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="pipeline.run_completed",
                data={"run_id": run_id},
            )
        )

        logger.info("Pipeline run completed: %s", run_id)
        return state

    async def _execute_delivery(self, artifacts: tuple[Path, ...], workspace: Path) -> None:
        """Run the delivery stage — send video + content to user."""
        from pipeline.infrastructure.adapters.content_parser import parse_content_output

        video_files = [a for a in artifacts if a.suffix == ".mp4"]
        content_files = [a for a in artifacts if a.name == "content.json"]

        if not video_files:
            logger.warning("No video artifact found for delivery")
            return

        video = video_files[-1]
        content_raw = ""
        if content_files:
            content_raw = await asyncio.to_thread(content_files[-1].read_text)

        if content_raw and self._delivery_handler is not None:
            content = parse_content_output(content_raw)
            await self._delivery_handler.deliver(video, content)
        elif self._delivery_handler is not None:
            logger.warning("No content.json found — delivering video only")
            await self._delivery_handler._deliver_video(video)

    def _build_request(
        self,
        stage: PipelineStage,
        workspace: Path,
        prior_artifacts: tuple[Path, ...],
        item: QueueItem,
    ) -> AgentRequest:
        """Build an AgentRequest for the given stage."""
        step_file_name, agent_dir, _ = _STAGE_DISPATCH[stage]

        step_file = self._workflows_dir / "stages" / step_file_name
        agent_def = self._workflows_dir.parent / "agents" / agent_dir / "agent.md"

        elicitation: dict[str, str] = {}
        if item.topic_focus:
            elicitation["topic_focus"] = item.topic_focus

        return AgentRequest(
            stage=stage,
            step_file=step_file,
            agent_definition=agent_def,
            prior_artifacts=prior_artifacts,
            elicitation_context=MappingProxyType(elicitation),
        )

    async def _load_gate_criteria(self, gate_name: str) -> str:
        """Load QA gate criteria from the workflows directory."""
        criteria_path = self._workflows_dir / "qa" / "gate-criteria" / f"{gate_name}-criteria.md"
        exists = await asyncio.to_thread(criteria_path.exists)
        if exists:
            return await asyncio.to_thread(criteria_path.read_text)
        logger.warning("Gate criteria not found: %s", criteria_path)
        return ""
