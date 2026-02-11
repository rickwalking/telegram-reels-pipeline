"""Tests for main.py — processing loop and crash recovery wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pipeline.app.main import _process_item, _resume_interrupted_runs
from pipeline.application.crash_recovery import RecoveryPlan
from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.errors import PipelineError
from pipeline.domain.models import QueueItem, RunState
from pipeline.domain.types import RunId


def _make_item(url: str = "https://youtube.com/watch?v=test") -> QueueItem:
    return QueueItem(url=url, telegram_update_id=1, queued_at=datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC))


def _make_completed_state() -> RunState:
    return RunState(
        run_id=RunId("run-001"),
        youtube_url="https://youtube.com/watch?v=test",
        current_stage=PipelineStage.COMPLETED,
        qa_status=QAStatus.PASSED,
        escalation_state=EscalationState.NONE,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


def _make_escalated_state() -> RunState:
    return RunState(
        run_id=RunId("run-002"),
        youtube_url="https://youtube.com/watch?v=test",
        current_stage=PipelineStage.CONTENT,
        qa_status=QAStatus.FAILED,
        escalation_state=EscalationState.QA_EXHAUSTED,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


def _make_orchestrator(
    pipeline_result: RunState | None = None,
    pipeline_error: Exception | None = None,
) -> SimpleNamespace:
    workspace_ctx = AsyncMock()
    workspace_ctx.__aenter__ = AsyncMock(return_value=Path("/tmp/workspace"))
    workspace_ctx.__aexit__ = AsyncMock(return_value=False)

    workspace_manager = MagicMock()
    workspace_manager.managed_workspace.return_value = workspace_ctx

    pipeline_runner = AsyncMock()
    if pipeline_error:
        pipeline_runner.run.side_effect = pipeline_error
    else:
        pipeline_runner.run.return_value = pipeline_result or _make_completed_state()

    queue_consumer = MagicMock()
    queue_consumer.complete = MagicMock()
    queue_consumer.fail = MagicMock()

    telegram_bot = AsyncMock()

    return SimpleNamespace(
        workspace_manager=workspace_manager,
        pipeline_runner=pipeline_runner,
        queue_consumer=queue_consumer,
        telegram_bot=telegram_bot,
        crash_recovery=None,
    )


class TestProcessItem:
    async def test_completes_queue_item_on_success(self) -> None:
        orch = _make_orchestrator()
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.queue_consumer.complete.assert_called_once_with(proc_path)
        orch.queue_consumer.fail.assert_not_called()

    async def test_fails_queue_item_on_pipeline_error(self) -> None:
        orch = _make_orchestrator(pipeline_error=PipelineError("boom"))
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.queue_consumer.fail.assert_called_once_with(proc_path)
        orch.queue_consumer.complete.assert_not_called()

    async def test_notifies_user_on_pipeline_error(self) -> None:
        orch = _make_orchestrator(pipeline_error=PipelineError("stage failed"))
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.telegram_bot.notify_user.assert_called_once()
        assert "stage failed" in orch.telegram_bot.notify_user.call_args[0][0]

    async def test_fails_queue_item_on_unexpected_error(self) -> None:
        orch = _make_orchestrator(pipeline_error=RuntimeError("unexpected"))
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.queue_consumer.fail.assert_called_once_with(proc_path)

    async def test_leaves_in_processing_on_escalation(self) -> None:
        orch = _make_orchestrator(pipeline_result=_make_escalated_state())
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.queue_consumer.complete.assert_not_called()
        orch.queue_consumer.fail.assert_not_called()

    async def test_no_crash_when_telegram_not_configured(self) -> None:
        orch = _make_orchestrator(pipeline_error=PipelineError("err"))
        orch.telegram_bot = None
        proc_path = Path("/tmp/queue/processing/item.json")

        await _process_item(orch, _make_item(), proc_path)

        orch.queue_consumer.fail.assert_called_once()


class TestResumeInterruptedRuns:
    async def test_skips_when_no_crash_recovery(self) -> None:
        orch = SimpleNamespace(crash_recovery=None, pipeline_runner=AsyncMock())
        await _resume_interrupted_runs(orch)
        # Should not raise

    async def test_skips_when_no_pipeline_runner(self) -> None:
        orch = SimpleNamespace(crash_recovery=AsyncMock(), pipeline_runner=None)
        await _resume_interrupted_runs(orch)
        # Should not raise

    async def test_resumes_interrupted_run(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        run_state = RunState(
            run_id=RunId("interrupted-run"),
            youtube_url="https://youtube.com/watch?v=int",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router", "research", "transcript"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path=str(workspace),
        )
        plan = RecoveryPlan(
            run_state=run_state,
            resume_from=PipelineStage.CONTENT,
            stages_remaining=(PipelineStage.CONTENT, PipelineStage.LAYOUT_DETECTIVE),
            stages_already_done=3,
        )

        crash_recovery = AsyncMock()
        crash_recovery.scan_and_recover.return_value = (plan,)

        pipeline_runner = AsyncMock()

        orch = SimpleNamespace(crash_recovery=crash_recovery, pipeline_runner=pipeline_runner)

        await _resume_interrupted_runs(orch)

        pipeline_runner.resume.assert_called_once_with(run_state, PipelineStage.CONTENT, workspace)

    async def test_skips_resume_if_workspace_missing(self) -> None:
        run_state = RunState(
            run_id=RunId("no-workspace"),
            youtube_url="https://youtube.com/watch?v=nw",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router",),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path="/nonexistent/path",
        )
        plan = RecoveryPlan(
            run_state=run_state,
            resume_from=PipelineStage.CONTENT,
            stages_remaining=(PipelineStage.CONTENT,),
            stages_already_done=1,
        )

        crash_recovery = AsyncMock()
        crash_recovery.scan_and_recover.return_value = (plan,)

        pipeline_runner = AsyncMock()

        orch = SimpleNamespace(crash_recovery=crash_recovery, pipeline_runner=pipeline_runner)

        await _resume_interrupted_runs(orch)

        pipeline_runner.resume.assert_not_called()

    async def test_skips_resume_if_no_workspace_path(self) -> None:
        run_state = RunState(
            run_id=RunId("empty-ws"),
            youtube_url="https://youtube.com/watch?v=ew",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router",),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path="",
        )
        plan = RecoveryPlan(
            run_state=run_state,
            resume_from=PipelineStage.CONTENT,
            stages_remaining=(PipelineStage.CONTENT,),
            stages_already_done=1,
        )

        crash_recovery = AsyncMock()
        crash_recovery.scan_and_recover.return_value = (plan,)

        pipeline_runner = AsyncMock()

        orch = SimpleNamespace(crash_recovery=crash_recovery, pipeline_runner=pipeline_runner)

        await _resume_interrupted_runs(orch)

        pipeline_runner.resume.assert_not_called()

    async def test_continues_after_resume_failure(self, tmp_path: Path) -> None:
        workspace1 = tmp_path / "ws1"
        workspace1.mkdir()
        workspace2 = tmp_path / "ws2"
        workspace2.mkdir()

        plan1 = RecoveryPlan(
            run_state=RunState(
                run_id=RunId("fail-run"),
                youtube_url="https://youtube.com/watch?v=f",
                current_stage=PipelineStage.CONTENT,
                stages_completed=("router",),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                workspace_path=str(workspace1),
            ),
            resume_from=PipelineStage.CONTENT,
            stages_remaining=(PipelineStage.CONTENT,),
            stages_already_done=1,
        )
        plan2 = RecoveryPlan(
            run_state=RunState(
                run_id=RunId("ok-run"),
                youtube_url="https://youtube.com/watch?v=o",
                current_stage=PipelineStage.ASSEMBLY,
                stages_completed=("router", "research"),
                created_at=datetime.now(UTC).isoformat(),
                updated_at=datetime.now(UTC).isoformat(),
                workspace_path=str(workspace2),
            ),
            resume_from=PipelineStage.ASSEMBLY,
            stages_remaining=(PipelineStage.ASSEMBLY,),
            stages_already_done=2,
        )

        crash_recovery = AsyncMock()
        crash_recovery.scan_and_recover.return_value = (plan1, plan2)

        pipeline_runner = AsyncMock()
        pipeline_runner.resume.side_effect = [PipelineError("fail"), None]

        orch = SimpleNamespace(crash_recovery=crash_recovery, pipeline_runner=pipeline_runner)

        await _resume_interrupted_runs(orch)

        assert pipeline_runner.resume.call_count == 2
