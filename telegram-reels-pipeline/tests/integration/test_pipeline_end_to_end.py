"""Integration tests — mocked end-to-end pipeline runs with fake adapters."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pipeline.application.crash_recovery import CrashRecoveryHandler
from pipeline.application.event_bus import EventBus
from pipeline.application.pipeline_runner import PipelineRunner
from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.models import (
    AgentRequest,
    QACritique,
    QueueItem,
    ReflectionResult,
    RunState,
)
from pipeline.domain.types import GateName, RunId
from pipeline.infrastructure.adapters.file_state_store import FileStateStore

# ---------------------------------------------------------------------------
# Fake adapters
# ---------------------------------------------------------------------------


class FakeStageRunner:
    """Stage runner that tracks calls and can simulate escalation."""

    def __init__(self, escalate_at: PipelineStage | None = None) -> None:
        self._escalate_at = escalate_at
        self.calls: list[PipelineStage] = []

    async def run_stage(self, request: AgentRequest, gate: GateName, gate_criteria: str) -> ReflectionResult:
        self.calls.append(request.stage)
        critique = QACritique(
            decision=QADecision.PASS,
            score=90,
            gate=gate,
            attempt=1,
            confidence=0.95,
        )
        return ReflectionResult(
            best_critique=critique,
            artifacts=(),
            attempts=1,
            escalation_needed=(request.stage == self._escalate_at),
        )


class FakeCliBackend:
    """Minimal workspace tracking backend."""

    def __init__(self) -> None:
        self.workspace: Path | None = None
        self.workspace_history: list[Path | None] = []

    def set_workspace(self, workspace: Path | None) -> None:
        self.workspace = workspace
        self.workspace_history.append(workspace)


class FakeMessaging:
    """In-memory messaging adapter."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self.files: list[tuple[Path, str]] = []

    async def ask_user(self, question: str) -> str:
        return "ok"

    async def notify_user(self, message: str) -> None:
        self.messages.append(message)

    async def send_file(self, path: Path, caption: str) -> None:
        self.files.append((path, caption))


def _make_item(url: str = "https://youtube.com/watch?v=end2end") -> QueueItem:
    return QueueItem(url=url, telegram_update_id=42, queued_at=datetime(2026, 2, 10, 14, 0, 0, tzinfo=UTC))


def _build_runner(
    tmp_path: Path,
    escalate_at: PipelineStage | None = None,
) -> tuple[PipelineRunner, FakeStageRunner, FileStateStore, EventBus, FakeCliBackend]:
    state_store = FileStateStore(base_dir=tmp_path / "runs")
    stage_runner = FakeStageRunner(escalate_at=escalate_at)
    event_bus = EventBus()
    backend = FakeCliBackend()

    workflows_dir = tmp_path / "workflows"
    (workflows_dir / "qa" / "gate-criteria").mkdir(parents=True)
    (tmp_path / "agents" / "router").mkdir(parents=True)

    runner = PipelineRunner(
        stage_runner=stage_runner,
        state_store=state_store,
        event_bus=event_bus,
        delivery_handler=None,
        workflows_dir=workflows_dir,
        cli_backend=backend,
    )
    return runner, stage_runner, state_store, event_bus, backend


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    async def test_all_stages_complete(self, tmp_path: Path) -> None:
        runner, stage_runner, state_store, _, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        state = await runner.run(_make_item(), workspace)

        assert state.current_stage == PipelineStage.COMPLETED
        assert state.qa_status == QAStatus.PASSED
        assert state.escalation_state == EscalationState.NONE
        assert len(state.stages_completed) == 9

    async def test_all_gated_stages_called(self, tmp_path: Path) -> None:
        runner, stage_runner, _, _, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        await runner.run(_make_item(), workspace)

        # 7 gated stages (DELIVERY and VEO3_AWAIT have no gate)
        assert len(stage_runner.calls) == 7
        assert PipelineStage.DELIVERY not in stage_runner.calls
        assert PipelineStage.VEO3_AWAIT not in stage_runner.calls

    async def test_state_persisted_to_disk(self, tmp_path: Path) -> None:
        runner, _, state_store, _, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        state = await runner.run(_make_item(), workspace)

        loaded = await state_store.load_state(state.run_id)
        assert loaded is not None
        assert loaded.current_stage == PipelineStage.COMPLETED

    async def test_events_published(self, tmp_path: Path) -> None:
        runner, _, _, event_bus, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        events: list[object] = []

        async def _capture(event: object) -> None:
            events.append(event)

        event_bus.subscribe(_capture)

        await runner.run(_make_item(), workspace)

        event_names = [e.event_name for e in events]
        assert "pipeline.run_started" in event_names
        assert "pipeline.run_completed" in event_names

    async def test_workspace_set_on_backend(self, tmp_path: Path) -> None:
        runner, _, _, _, backend = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        await runner.run(_make_item(), workspace)
        # Workspace was set for the run, then cleared
        assert workspace in backend.workspace_history
        assert backend.workspace is None  # cleared in finally


# ---------------------------------------------------------------------------
# Escalation
# ---------------------------------------------------------------------------


class TestEscalation:
    async def test_stops_at_escalated_stage(self, tmp_path: Path) -> None:
        runner, _, _, _, _ = _build_runner(tmp_path, escalate_at=PipelineStage.CONTENT)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        state = await runner.run(_make_item(), workspace)

        assert state.current_stage == PipelineStage.CONTENT
        assert state.escalation_state == EscalationState.QA_EXHAUSTED
        assert state.qa_status == QAStatus.FAILED

    async def test_escalation_persisted(self, tmp_path: Path) -> None:
        runner, _, state_store, _, _ = _build_runner(tmp_path, escalate_at=PipelineStage.RESEARCH)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        state = await runner.run(_make_item(), workspace)

        loaded = await state_store.load_state(state.run_id)
        assert loaded is not None
        assert loaded.escalation_state == EscalationState.QA_EXHAUSTED


# ---------------------------------------------------------------------------
# Crash recovery resume
# ---------------------------------------------------------------------------


class TestCrashRecoveryResume:
    async def test_resume_from_content(self, tmp_path: Path) -> None:
        runner, stage_runner, state_store, _, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        prior = RunState(
            run_id=RunId("crash-run-001"),
            youtube_url="https://youtube.com/watch?v=crash",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router", "research", "transcript"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path=str(workspace),
        )

        state = await runner.resume(prior, PipelineStage.CONTENT, workspace)

        assert state.current_stage == PipelineStage.COMPLETED
        assert state.run_id == RunId("crash-run-001")
        # Content + LD + FFmpeg + Assembly = 4 gated stages (delivery has no gate)
        assert PipelineStage.ROUTER not in stage_runner.calls
        assert PipelineStage.CONTENT in stage_runner.calls

    async def test_resume_persisted_to_disk(self, tmp_path: Path) -> None:
        runner, _, state_store, _, _ = _build_runner(tmp_path)
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        prior = RunState(
            run_id=RunId("crash-run-002"),
            youtube_url="https://youtube.com/watch?v=crash",
            current_stage=PipelineStage.ASSEMBLY,
            stages_completed=("router", "research", "transcript", "content", "layout_detective", "ffmpeg_engineer"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )

        await runner.resume(prior, PipelineStage.ASSEMBLY, workspace)
        loaded = await state_store.load_state(RunId("crash-run-002"))
        assert loaded is not None
        assert loaded.current_stage == PipelineStage.COMPLETED

    async def test_scan_and_recover_finds_incomplete_run(self, tmp_path: Path) -> None:
        state_store = FileStateStore(base_dir=tmp_path / "runs")
        messaging = FakeMessaging()
        handler = CrashRecoveryHandler(state_store=state_store, messaging=messaging)

        incomplete = RunState(
            run_id=RunId("interrupted-001"),
            youtube_url="https://youtube.com/watch?v=int",
            current_stage=PipelineStage.TRANSCRIPT,
            stages_completed=("router", "research"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            workspace_path="/some/path",
        )
        await state_store.save_state(incomplete)

        plans = await handler.scan_and_recover()
        assert len(plans) == 1
        assert plans[0].resume_from == PipelineStage.TRANSCRIPT
        assert plans[0].stages_already_done == 2

    async def test_scan_and_recover_notifies_user(self, tmp_path: Path) -> None:
        state_store = FileStateStore(base_dir=tmp_path / "runs")
        messaging = FakeMessaging()
        handler = CrashRecoveryHandler(state_store=state_store, messaging=messaging)

        incomplete = RunState(
            run_id=RunId("interrupted-002"),
            youtube_url="https://youtube.com/watch?v=int",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router", "research", "transcript"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        await state_store.save_state(incomplete)

        await handler.scan_and_recover()
        assert len(messaging.messages) == 1
        assert "content" in messaging.messages[0].lower()
