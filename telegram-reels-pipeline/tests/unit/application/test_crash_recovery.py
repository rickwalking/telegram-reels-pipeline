"""Tests for CrashRecoveryHandler — crash detection and resume planning."""

from __future__ import annotations

from pipeline.application.crash_recovery import (
    CrashRecoveryHandler,
    RecoveryPlan,
    _build_recovery_plan,
)
from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run(
    run_id: str = "run-001",
    stage: PipelineStage = PipelineStage.TRANSCRIPT,
    stages_completed: tuple[str, ...] = ("router", "research"),
) -> RunState:
    return RunState(
        run_id=RunId(run_id),
        youtube_url="https://www.youtube.com/watch?v=abc",
        current_stage=stage,
        stages_completed=stages_completed,
        escalation_state=EscalationState.NONE,
        qa_status=QAStatus.PENDING,
        created_at="2026-02-10T14:00:00Z",
        updated_at="2026-02-10T14:10:00Z",
    )


class FakeStateStore:
    """Stub implementing StateStorePort for testing."""

    def __init__(self, incomplete: list[RunState] | None = None) -> None:
        self._incomplete = incomplete or []
        self.saved: list[RunState] = []

    async def save_state(self, state: RunState) -> None:
        self.saved.append(state)

    async def load_state(self, run_id: RunId) -> RunState | None:
        for s in self._incomplete:
            if s.run_id == run_id:
                return s
        return None

    async def list_incomplete_runs(self) -> list[RunState]:
        return list(self._incomplete)


class FakeMessaging:
    """Stub implementing MessagingPort for testing."""

    def __init__(self) -> None:
        self.notifications: list[str] = []

    async def ask_user(self, question: str) -> str:
        return ""

    async def notify_user(self, message: str) -> None:
        self.notifications.append(message)

    async def send_file(self, path: object, caption: str) -> None:
        pass


# ---------------------------------------------------------------------------
# _build_recovery_plan tests
# ---------------------------------------------------------------------------

class TestBuildRecoveryPlan:
    def test_resumes_from_first_incomplete_stage(self) -> None:
        run = _make_run(stages_completed=("router", "research"))
        plan = _build_recovery_plan(run)

        assert plan is not None
        assert plan.resume_from == PipelineStage.TRANSCRIPT
        assert plan.stages_already_done == 2

    def test_resumes_from_beginning_when_no_stages_completed(self) -> None:
        run = _make_run(stages_completed=())
        plan = _build_recovery_plan(run)

        assert plan is not None
        assert plan.resume_from == PipelineStage.ROUTER
        assert plan.stages_already_done == 0
        assert len(plan.stages_remaining) == 8

    def test_remaining_stages_are_in_order(self) -> None:
        run = _make_run(stages_completed=("router", "research", "transcript", "content"))
        plan = _build_recovery_plan(run)

        assert plan is not None
        assert plan.resume_from == PipelineStage.LAYOUT_DETECTIVE
        assert plan.stages_remaining == (
            PipelineStage.LAYOUT_DETECTIVE,
            PipelineStage.FFMPEG_ENGINEER,
            PipelineStage.ASSEMBLY,
            PipelineStage.DELIVERY,
        )

    def test_returns_none_when_all_stages_completed(self) -> None:
        all_stages = (
            "router", "research", "transcript", "content",
            "layout_detective", "ffmpeg_engineer", "assembly", "delivery",
        )
        run = _make_run(stages_completed=all_stages)
        plan = _build_recovery_plan(run)

        assert plan is None

    def test_single_stage_remaining(self) -> None:
        completed = (
            "router", "research", "transcript", "content",
            "layout_detective", "ffmpeg_engineer", "assembly",
        )
        run = _make_run(stages_completed=completed)
        plan = _build_recovery_plan(run)

        assert plan is not None
        assert plan.resume_from == PipelineStage.DELIVERY
        assert plan.stages_remaining == (PipelineStage.DELIVERY,)

    def test_plan_is_frozen(self) -> None:
        run = _make_run()
        plan = _build_recovery_plan(run)
        assert plan is not None
        assert isinstance(plan, RecoveryPlan)

    def test_ignores_unknown_stage_strings(self) -> None:
        run = _make_run(stages_completed=("router", "bogus_stage", "research"))
        plan = _build_recovery_plan(run)

        assert plan is not None
        assert plan.resume_from == PipelineStage.TRANSCRIPT
        assert plan.stages_already_done == 2  # Only router + research counted


# ---------------------------------------------------------------------------
# CrashRecoveryHandler.scan_and_recover tests
# ---------------------------------------------------------------------------

class TestScanAndRecover:
    async def test_no_incomplete_runs_returns_empty(self) -> None:
        store = FakeStateStore(incomplete=[])
        handler = CrashRecoveryHandler(state_store=store)

        plans = await handler.scan_and_recover()

        assert plans == ()

    async def test_finds_single_interrupted_run(self) -> None:
        run = _make_run(stages_completed=("router",))
        store = FakeStateStore(incomplete=[run])
        handler = CrashRecoveryHandler(state_store=store)

        plans = await handler.scan_and_recover()

        assert len(plans) == 1
        assert plans[0].resume_from == PipelineStage.RESEARCH
        assert plans[0].stages_already_done == 1

    async def test_finds_multiple_interrupted_runs(self) -> None:
        run1 = _make_run(run_id="run-001", stages_completed=("router",))
        run2 = _make_run(run_id="run-002", stages_completed=("router", "research", "transcript"))
        store = FakeStateStore(incomplete=[run1, run2])
        handler = CrashRecoveryHandler(state_store=store)

        plans = await handler.scan_and_recover()

        assert len(plans) == 2
        assert plans[0].resume_from == PipelineStage.RESEARCH
        assert plans[1].resume_from == PipelineStage.CONTENT

    async def test_notifies_user_on_resume(self) -> None:
        run = _make_run(stages_completed=("router", "research"))
        store = FakeStateStore(incomplete=[run])
        messaging = FakeMessaging()
        handler = CrashRecoveryHandler(state_store=store, messaging=messaging)

        await handler.scan_and_recover()

        assert len(messaging.notifications) == 1
        assert "transcript" in messaging.notifications[0]
        assert "2 of 8" in messaging.notifications[0]

    async def test_no_notification_without_messaging(self) -> None:
        run = _make_run(stages_completed=("router",))
        store = FakeStateStore(incomplete=[run])
        handler = CrashRecoveryHandler(state_store=store, messaging=None)

        plans = await handler.scan_and_recover()

        assert len(plans) == 1

    async def test_notification_failure_does_not_crash(self) -> None:
        run = _make_run(stages_completed=("router",))
        store = FakeStateStore(incomplete=[run])

        class FailingMessaging(FakeMessaging):
            async def notify_user(self, message: str) -> None:
                raise ConnectionError("Telegram down")

        handler = CrashRecoveryHandler(state_store=store, messaging=FailingMessaging())

        plans = await handler.scan_and_recover()

        assert len(plans) == 1

    async def test_skips_inconsistent_runs(self) -> None:
        all_stages = (
            "router", "research", "transcript", "content",
            "layout_detective", "ffmpeg_engineer", "assembly", "delivery",
        )
        run = _make_run(stages_completed=all_stages, stage=PipelineStage.DELIVERY)
        store = FakeStateStore(incomplete=[run])
        handler = CrashRecoveryHandler(state_store=store)

        plans = await handler.scan_and_recover()

        assert plans == ()
