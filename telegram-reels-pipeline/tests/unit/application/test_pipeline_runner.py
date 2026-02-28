"""Tests for PipelineRunner — end-to-end pipeline orchestration."""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.application.pipeline_runner import _STAGE_SEQUENCE, PipelineRunner, _generate_run_id
from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.models import QACritique, QueueItem, ReflectionResult, RunState
from pipeline.domain.types import GateName, RunId


def _make_item(url: str = "https://youtube.com/watch?v=abc123") -> QueueItem:
    return QueueItem(
        url=url,
        telegram_update_id=42,
        queued_at=datetime(2025, 1, 1),
    )


def _make_reflection_result(escalation: bool = False) -> ReflectionResult:
    return ReflectionResult(
        best_critique=QACritique(
            decision=QADecision.PASS,
            score=90,
            gate=GateName("test"),
            attempt=1,
            confidence=0.95,
        ),
        artifacts=(Path("/tmp/artifact.md"),),
        attempts=1,
        escalation_needed=escalation,
    )


def _make_runner(
    escalation_at_stage: PipelineStage | None = None,
    workflows_dir: Path | None = None,
) -> tuple[PipelineRunner, MagicMock, MagicMock, MagicMock]:
    stage_runner = MagicMock()

    def run_stage_side_effect(request, gate, gate_criteria):
        if escalation_at_stage and request.stage == escalation_at_stage:
            return _make_reflection_result(escalation=True)
        return _make_reflection_result()

    stage_runner.run_stage = AsyncMock(side_effect=run_stage_side_effect)

    state_store = MagicMock()
    state_store.save_state = AsyncMock()

    event_bus = MagicMock()
    event_bus.publish = AsyncMock()

    delivery_handler = MagicMock()
    delivery_handler.deliver = AsyncMock()
    delivery_handler._deliver_video = AsyncMock()

    wf_dir = workflows_dir or Path("/tmp/workflows")

    runner = PipelineRunner(
        stage_runner=stage_runner,
        state_store=state_store,
        event_bus=event_bus,
        delivery_handler=delivery_handler,
        workflows_dir=wf_dir,
    )
    return runner, stage_runner, state_store, event_bus


class TestPipelineRunnerSuccess:
    async def test_completes_all_stages(self, tmp_path: Path) -> None:
        runner, stage_runner, _, _ = _make_runner()
        result = await runner.run(_make_item(), tmp_path)

        assert result.current_stage == PipelineStage.COMPLETED
        assert result.qa_status == QAStatus.PASSED

    async def test_run_id_generated(self, tmp_path: Path) -> None:
        runner, _, _, _ = _make_runner()
        result = await runner.run(_make_item(), tmp_path)

        assert result.run_id  # Not empty

    async def test_state_saved_multiple_times(self, tmp_path: Path) -> None:
        runner, _, state_store, _ = _make_runner()
        await runner.run(_make_item(), tmp_path)

        # Initial + per-stage (before + after) + final
        assert state_store.save_state.call_count > len(_STAGE_SEQUENCE)

    async def test_events_published(self, tmp_path: Path) -> None:
        runner, _, _, event_bus = _make_runner()
        await runner.run(_make_item(), tmp_path)

        events = [call.args[0] for call in event_bus.publish.call_args_list]
        event_names = [e.event_name for e in events]
        assert "pipeline.run_started" in event_names
        assert "pipeline.run_completed" in event_names

    async def test_stages_completed_accumulated(self, tmp_path: Path) -> None:
        runner, _, state_store, _ = _make_runner()
        await runner.run(_make_item(), tmp_path)

        # Check final save has all stages
        final_state = state_store.save_state.call_args_list[-1].args[0]
        assert final_state.current_stage == PipelineStage.COMPLETED

    async def test_stage_runner_called_for_gated_stages(self, tmp_path: Path) -> None:
        runner, stage_runner, _, _ = _make_runner()
        await runner.run(_make_item(), tmp_path)

        # All stages except DELIVERY and VEO3_AWAIT have gates
        non_gated = {PipelineStage.DELIVERY, PipelineStage.VEO3_AWAIT}
        gated_count = sum(1 for s in _STAGE_SEQUENCE if s not in non_gated)
        assert stage_runner.run_stage.call_count == gated_count


class TestPipelineRunnerEscalation:
    async def test_escalation_stops_pipeline(self, tmp_path: Path) -> None:
        runner, _, _, _ = _make_runner(escalation_at_stage=PipelineStage.RESEARCH)
        result = await runner.run(_make_item(), tmp_path)

        assert result.current_stage == PipelineStage.RESEARCH
        assert result.qa_status == QAStatus.FAILED
        assert result.escalation_state == EscalationState.QA_EXHAUSTED

    async def test_escalation_saves_state(self, tmp_path: Path) -> None:
        runner, _, state_store, _ = _make_runner(escalation_at_stage=PipelineStage.ROUTER)
        await runner.run(_make_item(), tmp_path)

        last_state = state_store.save_state.call_args_list[-1].args[0]
        assert last_state.escalation_state == EscalationState.QA_EXHAUSTED


class TestBuildRequest:
    def test_builds_request_with_correct_stage(self) -> None:
        runner, _, _, _ = _make_runner(workflows_dir=Path("/wf"))
        request = runner._build_request(
            PipelineStage.ROUTER,
            Path("/workspace"),
            (),
            _make_item(),
        )
        assert request.stage == PipelineStage.ROUTER
        assert "stage-01-router.md" in str(request.step_file)
        assert "router" in str(request.agent_definition)

    def test_includes_topic_focus_in_elicitation(self) -> None:
        runner, _, _, _ = _make_runner(workflows_dir=Path("/wf"))
        item = QueueItem(
            url="https://youtube.com/watch?v=abc",
            telegram_update_id=1,
            queued_at=datetime(2025, 1, 1),
            topic_focus="AI safety",
        )
        request = runner._build_request(
            PipelineStage.CONTENT,
            Path("/workspace"),
            (),
            item,
        )
        assert request.elicitation_context["topic_focus"] == "AI safety"

    def test_no_topic_focus_empty_elicitation(self) -> None:
        runner, _, _, _ = _make_runner(workflows_dir=Path("/wf"))
        request = runner._build_request(
            PipelineStage.ROUTER,
            Path("/workspace"),
            (),
            _make_item(),
        )
        assert len(request.elicitation_context) == 0

    def test_prior_artifacts_passed_through(self) -> None:
        runner, _, _, _ = _make_runner(workflows_dir=Path("/wf"))
        artifacts = (Path("/tmp/a.md"), Path("/tmp/b.md"))
        request = runner._build_request(
            PipelineStage.RESEARCH,
            Path("/workspace"),
            artifacts,
            _make_item(),
        )
        assert request.prior_artifacts == artifacts


class TestLoadGateCriteria:
    async def test_loads_existing_criteria(self, tmp_path: Path) -> None:
        criteria_dir = tmp_path / "qa" / "gate-criteria"
        criteria_dir.mkdir(parents=True)
        criteria_file = criteria_dir / "router-criteria.md"
        criteria_file.write_text("# Router Gate\nMust have valid URL.")

        runner, _, _, _ = _make_runner(workflows_dir=tmp_path)
        result = await runner._load_gate_criteria("router")
        assert "Must have valid URL" in result

    async def test_missing_criteria_returns_empty(self, tmp_path: Path) -> None:
        runner, _, _, _ = _make_runner(workflows_dir=tmp_path)
        result = await runner._load_gate_criteria("nonexistent")
        assert result == ""


class TestGenerateRunId:
    def test_not_empty(self) -> None:
        run_id = _generate_run_id()
        assert run_id

    def test_contains_date_pattern(self) -> None:
        run_id = _generate_run_id()
        # Should contain YYYYMMDD-HHMMSS pattern
        assert "-" in run_id

    def test_unique_across_calls(self) -> None:
        ids = {_generate_run_id() for _ in range(10)}
        assert len(ids) == 10


class TestStageSequence:
    def test_sequence_length(self) -> None:
        assert len(_STAGE_SEQUENCE) == 9

    def test_starts_with_router(self) -> None:
        assert _STAGE_SEQUENCE[0] == PipelineStage.ROUTER

    def test_ends_with_delivery(self) -> None:
        assert _STAGE_SEQUENCE[-1] == PipelineStage.DELIVERY


class TestPipelineRunnerWorkspace:
    async def test_sets_workspace_on_cli_backend(self, tmp_path: Path) -> None:
        cli_backend = MagicMock()
        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=_make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            cli_backend=cli_backend,
        )
        workspace = tmp_path / "ws"
        workspace.mkdir()
        await runner.run(_make_item(), workspace)
        # First call sets workspace, second call clears it
        calls = cli_backend.set_workspace.call_args_list
        assert calls[0].args[0] == workspace
        assert calls[1].args[0] is None

    async def test_workspace_path_stored_in_state(self, tmp_path: Path) -> None:
        state_store = MagicMock(save_state=AsyncMock())
        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=_make_reflection_result())),
            state_store=state_store,
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
        )
        workspace = tmp_path / "ws"
        workspace.mkdir()
        result = await runner.run(_make_item(), workspace)
        assert result.workspace_path == str(workspace)


class TestPipelineRunnerResume:
    def _prior_state(
        self,
        stages_completed: tuple[str, ...] = ("router", "research", "transcript"),
        stage: PipelineStage = PipelineStage.CONTENT,
    ) -> RunState:
        return RunState(
            run_id=RunId("resume-test-001"),
            youtube_url="https://youtube.com/watch?v=resume",
            current_stage=stage,
            stages_completed=stages_completed,
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path="/old/workspace",
        )

    async def test_resume_completes_remaining_stages(self, tmp_path: Path) -> None:
        runner, stage_runner, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        state = await runner.resume(
            self._prior_state(),
            PipelineStage.CONTENT,
            workspace,
        )
        assert state.current_stage == PipelineStage.COMPLETED
        assert state.qa_status == QAStatus.PASSED

    async def test_resume_skips_earlier_stages(self, tmp_path: Path) -> None:
        runner, stage_runner, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        await runner.resume(
            self._prior_state(),
            PipelineStage.CONTENT,
            workspace,
        )

        called_stages = [call.args[0].stage for call in stage_runner.run_stage.call_args_list]
        assert PipelineStage.ROUTER not in called_stages
        assert PipelineStage.RESEARCH not in called_stages
        assert PipelineStage.CONTENT in called_stages

    async def test_resume_preserves_run_id(self, tmp_path: Path) -> None:
        runner, _, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        state = await runner.resume(
            self._prior_state(),
            PipelineStage.CONTENT,
            workspace,
        )
        assert state.run_id == RunId("resume-test-001")

    async def test_resume_publishes_resumed_event(self, tmp_path: Path) -> None:
        runner, _, _, event_bus = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        await runner.resume(
            self._prior_state(),
            PipelineStage.CONTENT,
            workspace,
        )

        events = [call.args[0] for call in event_bus.publish.call_args_list]
        event_names = [e.event_name for e in events]
        assert "pipeline.run_resumed" in event_names
        assert "pipeline.run_completed" in event_names

    async def test_resume_stops_on_escalation(self, tmp_path: Path) -> None:
        runner, _, _, _ = _make_runner(escalation_at_stage=PipelineStage.FFMPEG_ENGINEER)
        workspace = tmp_path / "ws"
        workspace.mkdir()

        prior = self._prior_state(
            stages_completed=("router", "research", "transcript", "content", "layout_detective"),
            stage=PipelineStage.FFMPEG_ENGINEER,
        )
        state = await runner.resume(prior, PipelineStage.FFMPEG_ENGINEER, workspace)
        assert state.escalation_state == EscalationState.QA_EXHAUSTED
        assert state.current_stage == PipelineStage.FFMPEG_ENGINEER

    async def test_resume_sets_workspace_on_backend(self, tmp_path: Path) -> None:
        cli_backend = MagicMock()
        stage_runner = MagicMock()
        stage_runner.run_stage = AsyncMock(return_value=_make_reflection_result())

        runner = PipelineRunner(
            stage_runner=stage_runner,
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            cli_backend=cli_backend,
        )
        workspace = tmp_path / "ws"
        workspace.mkdir()

        prior = self._prior_state(
            stages_completed=(
                "router",
                "research",
                "transcript",
                "content",
                "layout_detective",
                "ffmpeg_engineer",
                "assembly",
            ),
            stage=PipelineStage.DELIVERY,
        )
        await runner.resume(prior, PipelineStage.DELIVERY, workspace)
        calls = cli_backend.set_workspace.call_args_list
        assert calls[0].args[0] == workspace
        assert calls[1].args[0] is None


class TestExternalClipBackgroundTask:
    """Tests for external clip resolution background task lifecycle."""

    @staticmethod
    def _make_runner_with_downloader(
        tmp_path: Path,
        downloader: object | None = None,
    ) -> PipelineRunner:
        return PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=_make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            external_clip_downloader=downloader,  # type: ignore[arg-type]
        )

    async def test_background_task_launched_after_content(self, tmp_path: Path) -> None:
        downloader = AsyncMock()
        downloader.download = AsyncMock(return_value=None)
        runner = self._make_runner_with_downloader(tmp_path, downloader)

        # Write publishing-assets.json with suggestions
        workspace = tmp_path / "ws"
        workspace.mkdir()
        assets = {"external_clip_suggestions": [{"search_query": "ocean"}]}
        (workspace / "publishing-assets.json").write_text(json.dumps(assets))

        # Patch _search_youtube to avoid real yt-dlp calls
        with patch(
            "pipeline.application.external_clip_resolver.ExternalClipResolver._search_youtube",
            return_value=None,
        ):
            result = await runner.run(_make_item(), workspace)

        assert result.current_stage == PipelineStage.COMPLETED

    async def test_no_task_when_downloader_is_none(self, tmp_path: Path) -> None:
        runner = self._make_runner_with_downloader(tmp_path, downloader=None)

        workspace = tmp_path / "ws"
        workspace.mkdir()

        result = await runner.run(_make_item(), workspace)

        assert result.current_stage == PipelineStage.COMPLETED
        assert "external_clips" not in runner._background_tasks

    async def test_background_task_stored_in_dict(self, tmp_path: Path) -> None:
        downloader = AsyncMock()
        downloader.download = AsyncMock(return_value=None)
        runner = self._make_runner_with_downloader(tmp_path, downloader)

        workspace = tmp_path / "ws"
        workspace.mkdir()
        assets = {"external_clip_suggestions": [{"search_query": "nature"}]}
        (workspace / "publishing-assets.json").write_text(json.dumps(assets))

        task_seen = False

        original_dispatch = runner._dispatch_stage.__func__  # type: ignore[attr-defined]

        async def spy_dispatch(self_inner, stage, ws, artifacts, item, state):  # type: ignore[no-untyped-def]
            nonlocal task_seen
            # Check after CONTENT but before next stage
            if stage == PipelineStage.LAYOUT_DETECTIVE:
                task_seen = "external_clips" in self_inner._background_tasks
            return await original_dispatch(self_inner, stage, ws, artifacts, item, state)

        with (
            patch.object(type(runner), "_dispatch_stage", spy_dispatch),
            patch(
                "pipeline.application.external_clip_resolver.ExternalClipResolver._search_youtube",
                return_value=None,
            ),
        ):
            await runner.run(_make_item(), workspace)

        assert task_seen

    async def test_background_task_failure_does_not_crash_pipeline(self, tmp_path: Path) -> None:
        downloader = AsyncMock()
        downloader.download = AsyncMock(return_value=None)
        runner = self._make_runner_with_downloader(tmp_path, downloader)

        workspace = tmp_path / "ws"
        workspace.mkdir()
        assets = {"external_clip_suggestions": [{"search_query": "will-fail"}]}
        (workspace / "publishing-assets.json").write_text(json.dumps(assets))

        with patch(
            "pipeline.application.external_clip_resolver.ExternalClipResolver._search_youtube",
            side_effect=RuntimeError("Search engine down"),
        ):
            result = await runner.run(_make_item(), workspace)

        # Pipeline should still complete despite external clip failure
        assert result.current_stage == PipelineStage.COMPLETED

    async def test_no_suggestions_is_noop(self, tmp_path: Path) -> None:
        downloader = AsyncMock()
        runner = self._make_runner_with_downloader(tmp_path, downloader)

        workspace = tmp_path / "ws"
        workspace.mkdir()
        assets = {"descriptions": [{"text": "No clips"}]}
        (workspace / "publishing-assets.json").write_text(json.dumps(assets))

        result = await runner.run(_make_item(), workspace)

        assert result.current_stage == PipelineStage.COMPLETED
        # No manifest should be written if no suggestions
        assert not (workspace / "external-clips.json").exists()

    async def test_missing_publishing_assets_is_noop(self, tmp_path: Path) -> None:
        downloader = AsyncMock()
        runner = self._make_runner_with_downloader(tmp_path, downloader)

        workspace = tmp_path / "ws"
        workspace.mkdir()
        # No publishing-assets.json at all

        result = await runner.run(_make_item(), workspace)

        assert result.current_stage == PipelineStage.COMPLETED


class TestFireVeo3Background:
    """Tests for _fire_veo3_background exception handling."""

    def test_setup_exception_returns_none(self, tmp_path: Path) -> None:
        """When Veo3Orchestrator construction fails, returns None gracefully."""
        runner, _, _, _ = _make_runner()
        # Patch at source module so the deferred import picks up the mock
        with patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
            side_effect=RuntimeError("adapter init failed"),
        ):
            result = runner._fire_veo3_background(tmp_path, "run-err")

        assert result is None

    async def test_returns_task_on_success(self, tmp_path: Path) -> None:
        """When setup succeeds, returns an asyncio.Task."""
        import asyncio

        runner, _, _, _ = _make_runner()

        mock_orch = MagicMock()
        mock_orch.start_generation = AsyncMock(return_value=None)

        with patch(
            "pipeline.application.veo3_orchestrator.Veo3Orchestrator",
            return_value=mock_orch,
        ):
            task = runner._fire_veo3_background(tmp_path, "run-ok")

        assert task is not None
        assert isinstance(task, asyncio.Task)
        # Clean up task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


class TestRunVeo3AwaitGateException:
    """Tests for _run_veo3_await_gate exception handling in pipeline_runner."""

    async def test_gate_exception_does_not_crash_pipeline(self, tmp_path: Path) -> None:
        """When run_veo3_await_gate raises, pipeline continues."""
        runner, _, _, event_bus = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            side_effect=RuntimeError("gate exploded"),
        ):
            await runner._run_veo3_await_gate(workspace, "run-fail")

        # Events should still be published (started + completed)
        events = [call.args[0].event_name for call in event_bus.publish.call_args_list]
        assert "veo3.gate.started" in events
        assert "veo3.gate.completed" in events

    async def test_background_task_failure_handled(self, tmp_path: Path) -> None:
        """When _veo3_task raises, gate still runs."""
        runner, _, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()

        # Set a failing background task
        import asyncio

        async def _raise() -> None:
            raise RuntimeError("bg task died")

        runner._veo3_task = asyncio.ensure_future(_raise())
        # Let the task fail
        await asyncio.sleep(0)

        with patch(
            "pipeline.application.veo3_await_gate.run_veo3_await_gate",
            new_callable=AsyncMock,
            return_value={"skipped": True},
        ):
            await runner._run_veo3_await_gate(workspace, "run-bg-fail")

        # Task cleared
        assert runner._veo3_task is None


class TestBuildCutawayManifestException:
    """Tests for _build_cutaway_manifest exception handling."""

    async def test_manifest_build_exception_does_not_crash(self, tmp_path: Path) -> None:
        """When ManifestBuilder.build raises, pipeline continues."""
        runner, _, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()
        # Write encoding-plan so the first try block passes
        plan = {
            "commands": [{"start_s": 0, "end_s": 30, "transcript_text": "hello"}],
            "total_duration_seconds": 30.0,
        }
        (workspace / "encoding-plan.json").write_text(json.dumps(plan))

        with patch(
            "pipeline.application.manifest_builder.ManifestBuilder",
            side_effect=RuntimeError("builder exploded"),
        ):
            # Should not raise
            await runner._build_cutaway_manifest(workspace)

        # No manifest written
        assert not (workspace / "cutaway-manifest.json").exists()

    async def test_corrupt_encoding_plan_returns_silently(self, tmp_path: Path) -> None:
        """Corrupt encoding-plan.json -> returns without crash."""
        runner, _, _, _ = _make_runner()
        workspace = tmp_path / "ws"
        workspace.mkdir()
        (workspace / "encoding-plan.json").write_text("not json{{{")

        await runner._build_cutaway_manifest(workspace)

        assert not (workspace / "cutaway-manifest.json").exists()
