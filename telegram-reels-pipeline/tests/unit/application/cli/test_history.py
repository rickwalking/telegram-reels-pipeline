"""Tests for CommandHistory — append, persist, query, edge cases."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.application.cli.history import CommandHistory
from pipeline.domain.models import CommandRecord

# --- Helpers ---


def _make_record(
    name: str = "test",
    status: str = "success",
    error: str | None = None,
) -> CommandRecord:
    return CommandRecord(
        name=name,
        started_at="2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        status=status,
        error=error,
    )


# --- Tests ---


class TestCommandHistoryAppend:
    """Verify record appending."""

    def test_append_single(self) -> None:
        """Single append adds one record."""
        history = CommandHistory()
        record = _make_record()
        history.append(record)
        assert len(history) == 1
        assert history.all() == (record,)

    def test_append_preserves_order(self) -> None:
        """Multiple appends preserve insertion order."""
        history = CommandHistory()
        r1 = _make_record(name="first")
        r2 = _make_record(name="second")
        r3 = _make_record(name="third")
        history.append(r1)
        history.append(r2)
        history.append(r3)
        assert history.all() == (r1, r2, r3)


class TestCommandHistoryPersist:
    """Verify atomic write persistence."""

    def test_persist_writes_json(self, tmp_path: Path) -> None:
        """Persist creates a valid JSON file."""
        history = CommandHistory()
        history.append(_make_record(name="cmd-1"))
        history.append(_make_record(name="cmd-2", status="failed", error="boom"))

        history.persist(tmp_path)

        target = tmp_path / "command-history.json"
        assert target.exists()
        data = json.loads(target.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "cmd-1"
        assert data[0]["status"] == "success"
        assert data[0]["error"] is None
        assert data[1]["name"] == "cmd-2"
        assert data[1]["status"] == "failed"
        assert data[1]["error"] == "boom"

    def test_persist_overwrites_previous(self, tmp_path: Path) -> None:
        """Each persist overwrites the previous file content."""
        history = CommandHistory()
        history.append(_make_record(name="v1"))
        history.persist(tmp_path)

        history.append(_make_record(name="v2"))
        history.persist(tmp_path)

        data = json.loads((tmp_path / "command-history.json").read_text())
        assert len(data) == 2

    def test_persist_no_temp_files_left(self, tmp_path: Path) -> None:
        """No .tmp files left behind after persist."""
        history = CommandHistory()
        history.append(_make_record())
        history.persist(tmp_path)

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_persist_skips_when_workspace_none(self) -> None:
        """Persist with None workspace does not raise."""
        history = CommandHistory()
        history.append(_make_record())
        history.persist(None)  # Should log warning, not crash

    def test_persist_skips_when_workspace_missing(self, tmp_path: Path) -> None:
        """Persist with non-existent workspace does not raise."""
        history = CommandHistory()
        history.append(_make_record())
        missing = tmp_path / "nonexistent"
        history.persist(missing)  # Should log warning, not crash

    def test_persist_empty_history(self, tmp_path: Path) -> None:
        """Persist with no records writes empty JSON array."""
        history = CommandHistory()
        history.persist(tmp_path)

        data = json.loads((tmp_path / "command-history.json").read_text())
        assert data == []


class TestCommandHistoryQuery:
    """Verify query methods."""

    def test_all_returns_tuple(self) -> None:
        """all() returns a tuple, not a list."""
        history = CommandHistory()
        result = history.all()
        assert isinstance(result, tuple)
        assert result == ()

    def test_by_status_filters(self) -> None:
        """by_status() returns only matching records."""
        history = CommandHistory()
        history.append(_make_record(name="ok-1", status="success"))
        history.append(_make_record(name="fail-1", status="failed", error="e"))
        history.append(_make_record(name="ok-2", status="success"))

        successes = history.by_status("success")
        assert len(successes) == 2
        assert all(r.status == "success" for r in successes)

        failures = history.by_status("failed")
        assert len(failures) == 1
        assert failures[0].name == "fail-1"

    def test_by_status_no_match(self) -> None:
        """by_status() returns empty tuple when no records match."""
        history = CommandHistory()
        history.append(_make_record(status="success"))
        assert history.by_status("failed") == ()

    def test_last_returns_tail(self) -> None:
        """last(n) returns the last n records."""
        history = CommandHistory()
        for i in range(5):
            history.append(_make_record(name=f"cmd-{i}"))

        result = history.last(2)
        assert len(result) == 2
        assert result[0].name == "cmd-3"
        assert result[1].name == "cmd-4"

    def test_last_more_than_available(self) -> None:
        """last(n) with n > len returns all records."""
        history = CommandHistory()
        history.append(_make_record(name="only"))
        result = history.last(10)
        assert len(result) == 1
        assert result[0].name == "only"

    def test_last_zero_returns_empty(self) -> None:
        """last(0) returns empty tuple."""
        history = CommandHistory()
        history.append(_make_record())
        assert history.last(0) == ()

    def test_last_negative_returns_empty(self) -> None:
        """last(-1) returns empty tuple."""
        history = CommandHistory()
        history.append(_make_record())
        assert history.last(-1) == ()

    def test_len(self) -> None:
        """len() reflects number of records."""
        history = CommandHistory()
        assert len(history) == 0
        history.append(_make_record())
        assert len(history) == 1
