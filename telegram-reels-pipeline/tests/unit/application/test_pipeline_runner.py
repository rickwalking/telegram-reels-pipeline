"""Tests for PipelineRunner — end-to-end pipeline orchestration."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from pipeline.application.pipeline_runner import _STAGE_SEQUENCE, PipelineRunner, _generate_run_id
from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.models import QACritique, QueueItem, ReflectionResult
from pipeline.domain.types import GateName


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

        # All stages except DELIVERY have gates
        gated_count = sum(1 for s in _STAGE_SEQUENCE if s != PipelineStage.DELIVERY)
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
        assert len(_STAGE_SEQUENCE) == 8

    def test_starts_with_router(self) -> None:
        assert _STAGE_SEQUENCE[0] == PipelineStage.ROUTER

    def test_ends_with_delivery(self) -> None:
        assert _STAGE_SEQUENCE[-1] == PipelineStage.DELIVERY
