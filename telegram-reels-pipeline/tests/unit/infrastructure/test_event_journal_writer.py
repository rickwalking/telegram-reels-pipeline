"""Tests for EventJournalWriter — append events to events.log."""

from __future__ import annotations

from pathlib import Path

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import PipelineEvent
from pipeline.infrastructure.listeners.event_journal_writer import EventJournalWriter


def _make_event(
    name: str = "pipeline.stage_entered",
    stage: PipelineStage | None = PipelineStage.ROUTER,
    data: dict[str, object] | None = None,
) -> PipelineEvent:
    return PipelineEvent(
        timestamp="2026-02-10T14:30:00Z",
        event_name=name,
        stage=stage,
        data=data or {},
    )


class TestEventJournalWriter:
    async def test_appends_formatted_line(self, tmp_path: Path) -> None:
        log_path = tmp_path / "events.log"
        writer = EventJournalWriter(log_path)
        event = _make_event(data={"attempt": 1})

        await writer(event)

        content = log_path.read_text()
        assert '2026-02-10T14:30:00Z | pipeline.stage_entered | router | {"attempt":1}' in content

    async def test_appends_multiple_entries(self, tmp_path: Path) -> None:
        log_path = tmp_path / "events.log"
        writer = EventJournalWriter(log_path)

        await writer(_make_event("event.one"))
        await writer(_make_event("event.two"))

        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        log_path = tmp_path / "subdir" / "events.log"
        writer = EventJournalWriter(log_path)

        await writer(_make_event())

        assert log_path.exists()

    async def test_handles_none_stage(self, tmp_path: Path) -> None:
        log_path = tmp_path / "events.log"
        writer = EventJournalWriter(log_path)
        event = _make_event(stage=None)

        await writer(event)

        content = log_path.read_text()
        assert "| none |" in content

    async def test_empty_data_serialized(self, tmp_path: Path) -> None:
        log_path = tmp_path / "events.log"
        writer = EventJournalWriter(log_path)

        await writer(_make_event())

        content = log_path.read_text()
        assert "| {}" in content
