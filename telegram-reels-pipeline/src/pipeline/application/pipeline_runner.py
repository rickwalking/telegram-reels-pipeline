"""PipelineRunner — drive a full pipeline run through all 9 stages."""

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
    from pipeline.app.settings import PipelineSettings
    from pipeline.application.delivery_handler import DeliveryHandler
    from pipeline.application.event_bus import EventBus
    from pipeline.application.stage_runner import StageRunner
    from pipeline.domain.ports import ExternalClipDownloaderPort, StateStorePort, VideoGenerationPort
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
    PipelineStage.VEO3_AWAIT,
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
        settings: PipelineSettings | None = None,
        veo3_adapter: VideoGenerationPort | None = None,
        external_clip_downloader: ExternalClipDownloaderPort | None = None,
    ) -> None:
        self._stage_runner = stage_runner
        self._state_store = state_store
        self._event_bus = event_bus
        self._delivery_handler = delivery_handler
        self._workflows_dir = workflows_dir
        self._cli_backend = cli_backend
        self._settings = settings
        self._veo3_adapter = veo3_adapter
        self._external_clip_downloader = external_clip_downloader
        self._veo3_task: asyncio.Task[None] | None = None
        self._background_tasks: dict[str, asyncio.Task[None]] = {}

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

            escalated, artifacts = await self._dispatch_stage(stage, workspace, artifacts, item, state)
            if escalated is not None:
                return escalated

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

            # Fire async Veo3 generation after CONTENT stage (non-blocking)
            if stage == PipelineStage.CONTENT and self._veo3_adapter is not None:
                self._veo3_task = self._fire_veo3_background(workspace, state.run_id)

            # Fire external clip resolution after CONTENT stage (non-blocking)
            if stage == PipelineStage.CONTENT and self._external_clip_downloader is not None:
                self._fire_external_clips_background(workspace)

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
        through the normal execute -> QA -> recovery cycle.
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

            escalated, artifacts = await self._dispatch_stage(stage, workspace, artifacts, item, state)
            if escalated is not None:
                return escalated

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

            # Fire async Veo3 generation after CONTENT stage (non-blocking)
            if stage == PipelineStage.CONTENT and self._veo3_adapter is not None:
                self._veo3_task = self._fire_veo3_background(workspace, state.run_id)

            # Fire external clip resolution after CONTENT stage (non-blocking)
            if stage == PipelineStage.CONTENT and self._external_clip_downloader is not None:
                self._fire_external_clips_background(workspace)

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

    async def _dispatch_stage(
        self,
        stage: PipelineStage,
        workspace: Path,
        artifacts: tuple[Path, ...],
        item: QueueItem,
        state: RunState,
    ) -> tuple[RunState | None, tuple[Path, ...]]:
        """Execute a single pipeline stage, returning (escalated_state, artifacts).

        Returns ``(None, artifacts)`` on success; ``(state, artifacts)`` if
        escalation paused the pipeline.
        """
        # Await external clips background task before assembly
        if stage == PipelineStage.ASSEMBLY:
            await self._await_external_clips()

        if stage == PipelineStage.VEO3_AWAIT:
            await self._run_veo3_await_gate(workspace, state.run_id)
        elif stage in _STAGE_DISPATCH:
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
                    escalated = RunState(
                        run_id=state.run_id,
                        youtube_url=state.youtube_url,
                        current_stage=stage,
                        current_attempt=state.current_attempt,
                        qa_status=QAStatus.FAILED,
                        stages_completed=state.stages_completed,
                        escalation_state=EscalationState.QA_EXHAUSTED,
                        created_at=state.created_at,
                        updated_at=datetime.now(UTC).isoformat(),
                        workspace_path=state.workspace_path,
                    )
                    await self._state_store.save_state(escalated)
                    logger.warning("Pipeline paused at %s \u2014 escalation needed", stage.value)
                    return escalated, artifacts
            elif stage == PipelineStage.DELIVERY and self._delivery_handler is not None:
                await self._execute_delivery(artifacts, workspace)

        return None, artifacts

    def _fire_veo3_background(self, workspace: Path, run_id: str) -> asyncio.Task[None] | None:
        """Create a Veo3Orchestrator and fire start_generation as a background task.

        Returns the background task handle, or ``None`` on setup failure.
        Failures are logged but never crash the pipeline.
        """
        try:
            from pipeline.application.veo3_orchestrator import Veo3Orchestrator

            clip_count = 3
            timeout_s = 300
            if self._settings is not None:
                clip_count = self._settings.veo3_clip_count
                timeout_s = self._settings.veo3_timeout_s

            orchestrator = Veo3Orchestrator(
                video_gen=self._veo3_adapter,  # type: ignore[arg-type]
                clip_count=clip_count,
                timeout_s=timeout_s,
            )

            task: asyncio.Task[None] = asyncio.create_task(
                orchestrator.start_generation(workspace, run_id),
                name=f"veo3-gen-{run_id}",
            )
            logger.info("Veo3 background generation fired for run %s", run_id)
            return task
        except Exception:
            logger.warning("Veo3 generation fire failed \u2014 continuing pipeline", exc_info=True)
            return None

    async def _run_veo3_await_gate(self, workspace: Path, run_id: str) -> None:
        """Block before Assembly until all Veo3 jobs resolve or timeout.

        Awaits any background Veo3 generation task, then runs the polling
        gate.  Failures are logged but never crash the pipeline (graceful
        degradation).
        """
        from pipeline.application.veo3_await_gate import run_veo3_await_gate

        now = datetime.now(UTC).isoformat()
        await self._event_bus.publish(
            PipelineEvent(
                timestamp=now,
                event_name="veo3.gate.started",
                data={"run_id": run_id},
            )
        )

        try:
            # Await background generation task if it exists
            if self._veo3_task is not None:
                try:
                    await self._veo3_task
                except Exception:
                    logger.warning("Veo3 background task failed", exc_info=True)
                finally:
                    self._veo3_task = None

            timeout_s = 300
            if self._settings is not None:
                timeout_s = self._settings.veo3_timeout_s

            orchestrator = None
            if self._veo3_adapter is not None:
                from pipeline.application.veo3_orchestrator import Veo3Orchestrator

                clip_count = 3
                if self._settings is not None:
                    clip_count = self._settings.veo3_clip_count

                orchestrator = Veo3Orchestrator(
                    video_gen=self._veo3_adapter,
                    clip_count=clip_count,
                    timeout_s=timeout_s,
                )

            summary = await run_veo3_await_gate(
                workspace=workspace,
                orchestrator=orchestrator,
                timeout_s=timeout_s,
                event_bus=self._event_bus,
            )
            logger.info("Veo3 await gate result: %s", summary)
        except Exception:
            logger.warning("Veo3 await gate failed — continuing pipeline", exc_info=True)

        await self._event_bus.publish(
            PipelineEvent(
                timestamp=datetime.now(UTC).isoformat(),
                event_name="veo3.gate.completed",
                data={"run_id": run_id},
            )
        )

    def _fire_external_clips_background(self, workspace: Path) -> None:
        """Launch external clip resolution as a background asyncio.Task.

        Reads ``publishing-assets.json`` for ``external_clip_suggestions``,
        then resolves each via YouTube search + download.  The task is stored
        in ``_background_tasks["external_clips"]`` and awaited before assembly.
        Failures are logged but never crash the pipeline.
        """
        try:
            task: asyncio.Task[None] = asyncio.create_task(
                self._resolve_external_clips_safe(workspace),
                name="external-clips",
            )
            self._background_tasks["external_clips"] = task
            logger.info("External clip resolution fired as background task")
        except Exception:
            logger.warning("External clip resolution fire failed \u2014 continuing pipeline", exc_info=True)

    async def _resolve_external_clips_safe(self, workspace: Path) -> None:
        """Safe wrapper: resolve external clips, catching all exceptions."""
        try:
            await self._resolve_external_clips(workspace)
        except Exception:
            logger.exception("External clip resolution failed \u2014 continuing without external clips")

    async def _resolve_external_clips(self, workspace: Path) -> None:
        """Read suggestions from publishing-assets.json, search + download clips."""
        import json as _json

        assets_path = workspace / "publishing-assets.json"
        try:
            raw = await asyncio.to_thread(assets_path.read_text)
            data = _json.loads(raw)
        except (FileNotFoundError, _json.JSONDecodeError, OSError) as exc:
            logger.debug("Cannot read publishing-assets.json for external clips: %s", exc)
            return

        suggestions = data.get("external_clip_suggestions", [])
        if not isinstance(suggestions, list) or not suggestions:
            logger.debug("No external_clip_suggestions found \u2014 skipping")
            return

        from pipeline.application.external_clip_resolver import ExternalClipResolver

        resolver = ExternalClipResolver(self._external_clip_downloader)  # type: ignore[arg-type]
        resolved = await resolver.resolve_all(suggestions, workspace)
        await resolver.write_manifest(resolved, workspace)
        logger.info("External clip resolution complete: %d clips resolved", len(resolved))

    async def _await_external_clips(self) -> None:
        """Await background external clips task if it exists.  Non-fatal on failure."""
        task = self._background_tasks.pop("external_clips", None)
        if task is None:
            return
        try:
            await task
        except Exception:
            logger.warning("External clips background task failed", exc_info=True)

    async def _execute_delivery(self, artifacts: tuple[Path, ...], workspace: Path) -> None:
        """Run the delivery stage \u2014 send video + content to user."""
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
            logger.warning("No content.json found \u2014 delivering video only")
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

        if stage == PipelineStage.CONTENT and self._settings is not None and self._settings.publishing_language:
            elicitation["publishing_language"] = self._settings.publishing_language
            elicitation["publishing_description_variants"] = str(self._settings.publishing_description_variants)

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
