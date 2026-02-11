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
from pipeline.domain.models import AgentRequest, ContentPackage, PipelineEvent, QueueItem, RunState
from pipeline.domain.types import GateName, RunId

if TYPE_CHECKING:
    from pipeline.application.delivery_handler import DeliveryHandler
    from pipeline.application.event_bus import EventBus
    from pipeline.application.stage_runner import StageRunner
    from pipeline.domain.ports import StateStorePort
    from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend

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
        cli_backend: CliBackend | None = None,
    ) -> None:
        self._stage_runner = stage_runner
        self._state_store = state_store
        self._event_bus = event_bus
        self._delivery_handler = delivery_handler
        self._workflows_dir = workflows_dir
        self._cli_backend = cli_backend

    async def run(self, item: QueueItem, workspace: Path) -> RunState:
        """Execute a full pipeline run for a queue item.

        Creates initial RunState, drives through all stages in sequence,
        and delivers the final output. Returns the final RunState.
        """
        run_id = _generate_run_id()

        # Set per-run workspace on CLI backend so agent subprocesses run there
        if self._cli_backend is not None:
            self._cli_backend.set_workspace(workspace)

        try:
            return await self._run_stages(run_id, item, workspace)
        finally:
            if self._cli_backend is not None:
                self._cli_backend.set_workspace(None)

    async def _run_stages(self, run_id: RunId, item: QueueItem, workspace: Path) -> RunState:
        """Internal: execute all stages for a new run."""
        now = datetime.now(UTC).isoformat()

        state = RunState(
            run_id=run_id,
            youtube_url=item.url,
            current_stage=_STAGE_SEQUENCE[0],
            current_attempt=1,
            qa_status=QAStatus.PENDING,
            created_at=now,
            updated_at=now,
            workspace_path=str(workspace),
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
        ws_path = str(workspace)
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
                workspace_path=ws_path,
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
                        workspace_path=ws_path,
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
                workspace_path=ws_path,
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
            workspace_path=ws_path,
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

    async def resume(self, run_state: RunState, resume_from: PipelineStage, workspace: Path) -> RunState:
        """Resume an interrupted pipeline run from a specific stage.

        Skips already-completed stages and drives the remaining stages
        through the normal execute → QA → recovery cycle.
        """
        if self._cli_backend is not None:
            self._cli_backend.set_workspace(workspace)

        try:
            return await self._resume_stages(run_state, resume_from, workspace)
        finally:
            if self._cli_backend is not None:
                self._cli_backend.set_workspace(None)

    async def _resume_stages(self, run_state: RunState, resume_from: PipelineStage, workspace: Path) -> RunState:
        """Internal: execute remaining stages for a resumed run."""
        state = RunState(
            run_id=run_state.run_id,
            youtube_url=run_state.youtube_url,
            current_stage=resume_from,
            current_attempt=1,
            qa_status=QAStatus.PENDING,
            stages_completed=run_state.stages_completed,
            escalation_state=EscalationState.NONE,
            created_at=run_state.created_at,
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path=str(workspace),
        )
        await self._state_store.save_state(state)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="pipeline.run_resumed",
                data={"run_id": run_state.run_id, "resume_from": resume_from.value},
            )
        )

        # Build the remaining stage list starting from resume_from
        started = False
        remaining: list[PipelineStage] = []
        for stage in _STAGE_SEQUENCE:
            if stage == resume_from:
                started = True
            if started:
                remaining.append(stage)

        # Build a synthetic QueueItem for _build_request
        item = QueueItem(
            url=run_state.youtube_url,
            telegram_update_id=0,
            queued_at=datetime.fromisoformat(run_state.created_at) if run_state.created_at else datetime.now(UTC),
        )

        artifacts: tuple[Path, ...] = ()
        for stage in remaining:
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
                workspace_path=str(workspace),
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
                        workspace_path=str(workspace),
                    )
                    await self._state_store.save_state(state)
                    logger.warning("Resumed pipeline paused at %s — escalation needed", stage.value)
                    return state
            elif stage == PipelineStage.DELIVERY and self._delivery_handler is not None:
                await self._execute_delivery(artifacts, workspace)

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
                workspace_path=str(workspace),
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
            workspace_path=str(workspace),
        )
        await self._state_store.save_state(state)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="pipeline.run_completed",
                data={"run_id": run_state.run_id, "resumed": True},
            )
        )

        logger.info("Resumed pipeline run completed: %s", run_state.run_id)
        return state

    async def _execute_delivery(self, artifacts: tuple[Path, ...], workspace: Path) -> None:
        """Run the delivery stage — send video + content to user."""
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
            content = self._parse_content(content_raw)
            if content is not None:
                await self._delivery_handler.deliver(video, content)
            else:
                await self._delivery_handler.deliver_video_only(video)
        elif self._delivery_handler is not None:
            logger.warning("No content.json found — delivering video only")
            await self._delivery_handler.deliver_video_only(video)

    @staticmethod
    def _parse_content(raw: str) -> ContentPackage | None:
        """Parse content JSON into a ContentPackage, returning None on failure."""
        import json

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Failed to parse content.json")
            return None

        try:
            return ContentPackage(
                descriptions=tuple(data.get("descriptions", ())),
                hashtags=tuple(data.get("hashtags", ())),
                music_suggestion=data.get("music_suggestion", ""),
                mood_category=data.get("mood_category", ""),
            )
        except (ValueError, TypeError):
            logger.warning("Invalid content.json structure")
            return None

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
