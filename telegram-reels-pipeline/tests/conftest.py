"""Shared test fixtures for the pipeline test suite."""

import pytest

from pipeline.domain.enums import EscalationState, PipelineStage, QADecision, QAStatus
from pipeline.domain.models import PipelineEvent, QACritique, RunState
from pipeline.domain.types import GateName, RunId


@pytest.fixture
def sample_run_state() -> RunState:
    """Factory for a typical in-progress RunState."""
    return RunState(
        run_id=RunId("2026-02-10-abc123"),
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        current_stage=PipelineStage.RESEARCH,
        current_attempt=1,
        qa_status=QAStatus.PENDING,
        stages_completed=("router",),
        escalation_state=EscalationState.NONE,
        best_of_three_overrides=(),
        created_at="2026-02-10T14:00:00Z",
        updated_at="2026-02-10T14:05:00Z",
    )


@pytest.fixture
def sample_qa_critique() -> QACritique:
    """Factory for a typical passing QA critique."""
    return QACritique(
        decision=QADecision.PASS,
        score=92,
        gate=GateName("router"),
        attempt=1,
        blockers=(),
        prescriptive_fixes=(),
        confidence=0.95,
    )


@pytest.fixture
def sample_pipeline_event() -> PipelineEvent:
    """Factory for a typical pipeline event."""
    return PipelineEvent(
        timestamp="2026-02-10T14:00:00Z",
        event_name="pipeline.stage_entered",
        stage=PipelineStage.ROUTER,
        data={"attempt": 1},
    )
