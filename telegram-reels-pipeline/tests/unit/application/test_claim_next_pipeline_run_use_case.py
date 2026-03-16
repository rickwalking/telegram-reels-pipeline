"""Unit tests for ClaimNextPipelineRunUseCase — FIFO queue claim logic with faked ports."""

from __future__ import annotations

import pytest

from pipeline.domain.enums import RunExecutionStatus
from pipeline.domain.event_types import PIPELINE_RUN_CLAIMED
from pipeline.domain.events import PipelineStateEvent, RunStateProjection


class FakeEventStore:
    """In-memory fake implementing EventStorePort for unit tests."""

    def __init__(self) -> None:
        self.events: list[PipelineStateEvent] = []

    async def append_event(self, event: PipelineStateEvent) -> None:
        self.events.append(event)

    async def get_events_for_run(self, pipeline_run_id: str) -> tuple[PipelineStateEvent, ...]:
        return tuple(e for e in self.events if e.pipeline_run_id == pipeline_run_id)

    async def get_event_count_for_run(self, pipeline_run_id: str) -> int:
        return len([e for e in self.events if e.pipeline_run_id == pipeline_run_id])


class FakeStateStore:
    """In-memory fake implementing StateStorePort for unit tests."""

    def __init__(self) -> None:
        self.projections: dict[str, RunStateProjection] = {}

    async def save_state(self, projection: RunStateProjection) -> None:
        self.projections[projection.pipeline_run_id] = projection

    async def load_projection(self, pipeline_run_id: str) -> RunStateProjection | None:
        return self.projections.get(pipeline_run_id)

    async def list_by_execution_status(self, execution_status: str) -> list[RunStateProjection]:
        return [p for p in self.projections.values() if p.execution_status == execution_status]

    async def list_all_projections(self) -> list[RunStateProjection]:
        return list(self.projections.values())


def _make_pending_projection(
    pipeline_run_id: str = "20260316-120000-abc12345",
    youtube_url: str = "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    created_at: str = "2026-03-16T12:00:00+00:00",
) -> RunStateProjection:
    """Build a PENDING RunStateProjection for testing."""
    return RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url=youtube_url,
        trigger_source="api_client",
        current_stage="router",
        execution_status=RunExecutionStatus.PENDING.value,
        current_attempt_count=0,
        qa_evaluation_status="pending",
        completed_stages=(),
        escalation_status="none",
        created_at=created_at,
        last_updated_at=created_at,
    )


@pytest.fixture()
def fake_event_store() -> FakeEventStore:
    """Provide a fresh FakeEventStore."""
    return FakeEventStore()


@pytest.fixture()
def fake_state_store() -> FakeStateStore:
    """Provide a fresh FakeStateStore."""
    return FakeStateStore()


async def test_claims_oldest_pending_run(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should claim the oldest PENDING run (FIFO order)."""
    # Arrange
    from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

    older_projection = _make_pending_projection(
        pipeline_run_id="run-older",
        created_at="2026-03-16T10:00:00+00:00",
    )
    newer_projection = _make_pending_projection(
        pipeline_run_id="run-newer",
        created_at="2026-03-16T12:00:00+00:00",
    )
    await fake_state_store.save_state(older_projection)
    await fake_state_store.save_state(newer_projection)

    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    result = await use_case.execute()

    # Assert
    assert result is not None
    assert result.pipeline_run_id == "run-older"
    assert result.execution_status == RunExecutionStatus.IN_PROGRESS.value


async def test_returns_none_when_no_pending_runs(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should return None when no PENDING runs exist."""
    # Arrange
    from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    result = await use_case.execute()

    # Assert
    assert result is None
    assert len(fake_event_store.events) == 0


async def test_emits_claimed_event(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should emit a PIPELINE_RUN_CLAIMED event."""
    # Arrange
    from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

    projection = _make_pending_projection()
    await fake_state_store.save_state(projection)
    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    await use_case.execute()

    # Assert
    assert len(fake_event_store.events) == 1
    claimed_event = fake_event_store.events[0]
    assert claimed_event.event_type == PIPELINE_RUN_CLAIMED
    assert claimed_event.pipeline_run_id == projection.pipeline_run_id
    assert claimed_event.payload_data["new_status"] == RunExecutionStatus.IN_PROGRESS.value


async def test_updates_projection_in_state_store(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should persist the updated IN_PROGRESS projection."""
    # Arrange
    from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

    projection = _make_pending_projection(pipeline_run_id="run-to-claim")
    await fake_state_store.save_state(projection)
    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    await use_case.execute()

    # Assert
    loaded = await fake_state_store.load_projection("run-to-claim")
    assert loaded is not None
    assert loaded.execution_status == RunExecutionStatus.IN_PROGRESS.value


async def test_does_not_claim_in_progress_runs(
    fake_event_store: FakeEventStore,
    fake_state_store: FakeStateStore,
) -> None:
    """The use case should not claim runs that are already IN_PROGRESS."""
    # Arrange
    from pipeline.application.use_cases.claim_next_pipeline_run_use_case import ClaimNextPipelineRunUseCase

    in_progress_projection = RunStateProjection(
        pipeline_run_id="run-active",
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        trigger_source="api_client",
        current_stage="research",
        execution_status=RunExecutionStatus.IN_PROGRESS.value,
        created_at="2026-03-16T10:00:00+00:00",
        last_updated_at="2026-03-16T10:00:00+00:00",
    )
    await fake_state_store.save_state(in_progress_projection)
    use_case = ClaimNextPipelineRunUseCase(fake_event_store, fake_state_store)

    # Act
    result = await use_case.execute()

    # Assert
    assert result is None
    assert len(fake_event_store.events) == 0
