"""Unit tests for PipelineEventEmitterService pause and resume emit methods."""

from __future__ import annotations

import pytest

from pipeline.application.services.pipeline_event_emitter_service import (
    PipelineEventEmitterService,
    StageEventPayload,
)
from pipeline.domain.event_types import PIPELINE_PAUSED, PIPELINE_RESUMED
from pipeline.domain.events import RunStateProjection
from tests.fakes.fake_event_store import FakeEventStore
from tests.fakes.fake_state_store import FakeStateStore


def _seed_projection(
    fake_state_store: FakeStateStore,
    pipeline_run_id: str,
    stage_name: str = "research",
) -> RunStateProjection:
    """Helper to seed a projection into the fake state store synchronously."""
    import asyncio

    projection = RunStateProjection(
        pipeline_run_id=pipeline_run_id,
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        current_stage=stage_name,
        execution_status="running",
    )
    asyncio.get_event_loop().run_until_complete(fake_state_store.save_state(projection))
    return projection


@pytest.mark.asyncio
async def test_emit_pipeline_paused_appends_paused_event() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    fake_state_store = FakeStateStore()
    emitter = PipelineEventEmitterService(fake_event_store, fake_state_store)
    pipeline_run_id = "run-pause-test-001"
    await fake_state_store.save_state(
        RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://www.youtube.com/watch?v=testPause",
            current_stage="research",
            execution_status="running",
        )
    )
    pause_payload = StageEventPayload(pipeline_run_id=pipeline_run_id, stage_name="research")

    # Act
    await emitter.emit_pipeline_paused(pause_payload)

    # Assert
    assert len(fake_event_store.events) == 1
    emitted_event = fake_event_store.events[0]
    assert emitted_event.event_type == PIPELINE_PAUSED
    assert emitted_event.pipeline_run_id == pipeline_run_id
    assert emitted_event.stage_name == "research"


@pytest.mark.asyncio
async def test_emit_pipeline_paused_sets_projection_status_to_paused() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    fake_state_store = FakeStateStore()
    emitter = PipelineEventEmitterService(fake_event_store, fake_state_store)
    pipeline_run_id = "run-pause-test-002"
    await fake_state_store.save_state(
        RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://www.youtube.com/watch?v=testPause2",
            current_stage="content",
            execution_status="running",
        )
    )
    pause_payload = StageEventPayload(pipeline_run_id=pipeline_run_id, stage_name="content")

    # Act
    await emitter.emit_pipeline_paused(pause_payload)

    # Assert
    updated_projection = await fake_state_store.load_projection(pipeline_run_id)
    assert updated_projection is not None
    assert updated_projection.execution_status == "paused"


@pytest.mark.asyncio
async def test_emit_pipeline_resumed_appends_resumed_event() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    fake_state_store = FakeStateStore()
    emitter = PipelineEventEmitterService(fake_event_store, fake_state_store)
    pipeline_run_id = "run-resume-test-001"
    await fake_state_store.save_state(
        RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://www.youtube.com/watch?v=testResume",
            current_stage="transcript",
            execution_status="paused",
        )
    )
    resume_payload = StageEventPayload(pipeline_run_id=pipeline_run_id, stage_name="transcript")

    # Act
    await emitter.emit_pipeline_resumed(resume_payload)

    # Assert
    assert len(fake_event_store.events) == 1
    emitted_event = fake_event_store.events[0]
    assert emitted_event.event_type == PIPELINE_RESUMED
    assert emitted_event.pipeline_run_id == pipeline_run_id
    assert emitted_event.stage_name == "transcript"


@pytest.mark.asyncio
async def test_emit_pipeline_resumed_sets_projection_status_to_running() -> None:
    # Arrange
    fake_event_store = FakeEventStore()
    fake_state_store = FakeStateStore()
    emitter = PipelineEventEmitterService(fake_event_store, fake_state_store)
    pipeline_run_id = "run-resume-test-002"
    await fake_state_store.save_state(
        RunStateProjection(
            pipeline_run_id=pipeline_run_id,
            youtube_url="https://www.youtube.com/watch?v=testResume2",
            current_stage="layout_detective",
            execution_status="paused",
        )
    )
    resume_payload = StageEventPayload(pipeline_run_id=pipeline_run_id, stage_name="layout_detective")

    # Act
    await emitter.emit_pipeline_resumed(resume_payload)

    # Assert
    updated_projection = await fake_state_store.load_projection(pipeline_run_id)
    assert updated_projection is not None
    assert updated_projection.execution_status == "running"
