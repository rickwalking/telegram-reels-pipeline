"""Tests for CommandRecord frozen dataclass — fields, immutability, validation."""

from __future__ import annotations

import pytest

from pipeline.domain.models import CommandRecord

# --- Helpers ---


def _make_record(**overrides: object) -> CommandRecord:
    defaults: dict[str, object] = {
        "name": "test-cmd",
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "status": "success",
    }
    defaults.update(overrides)
    return CommandRecord(**defaults)  # type: ignore[arg-type]


# --- Tests ---


class TestCommandRecordConstruction:
    """Verify valid construction."""

    def test_success_record(self) -> None:
        """Successful command record with no error."""
        record = _make_record()
        assert record.name == "test-cmd"
        assert record.status == "success"
        assert record.error is None

    def test_failed_record(self) -> None:
        """Failed command record with error message."""
        record = _make_record(status="failed", error="something broke")
        assert record.status == "failed"
        assert record.error == "something broke"

    def test_failed_record_no_error_message(self) -> None:
        """Failed record without error message is valid."""
        record = _make_record(status="failed")
        assert record.status == "failed"
        assert record.error is None


class TestCommandRecordImmutability:
    """Verify frozen dataclass is immutable."""

    def test_cannot_set_name(self) -> None:
        """Setting name after construction raises FrozenInstanceError."""
        record = _make_record()
        with pytest.raises(AttributeError):
            record.name = "new-name"  # type: ignore[misc]

    def test_cannot_set_status(self) -> None:
        """Setting status after construction raises FrozenInstanceError."""
        record = _make_record()
        with pytest.raises(AttributeError):
            record.status = "failed"  # type: ignore[misc]

    def test_cannot_set_error(self) -> None:
        """Setting error after construction raises FrozenInstanceError."""
        record = _make_record()
        with pytest.raises(AttributeError):
            record.error = "oops"  # type: ignore[misc]


class TestCommandRecordValidation:
    """Verify __post_init__ validation rules."""

    def test_empty_name_raises(self) -> None:
        """Empty name is rejected."""
        with pytest.raises(ValueError, match="name must not be empty"):
            _make_record(name="")

    def test_empty_started_at_raises(self) -> None:
        """Empty started_at is rejected."""
        with pytest.raises(ValueError, match="started_at must not be empty"):
            _make_record(started_at="")

    def test_empty_finished_at_raises(self) -> None:
        """Empty finished_at is rejected."""
        with pytest.raises(ValueError, match="finished_at must not be empty"):
            _make_record(finished_at="")

    def test_invalid_status_raises(self) -> None:
        """Status other than 'success' or 'failed' is rejected."""
        with pytest.raises(ValueError, match="status must be 'success' or 'failed'"):
            _make_record(status="pending")

    def test_invalid_status_unknown(self) -> None:
        """Unknown status value is rejected."""
        with pytest.raises(ValueError, match="status must be 'success' or 'failed'"):
            _make_record(status="cancelled")


class TestCommandRecordEquality:
    """Verify equality and hashing for frozen dataclass."""

    def test_equal_records(self) -> None:
        """Two records with same values are equal."""
        r1 = _make_record()
        r2 = _make_record()
        assert r1 == r2

    def test_different_records(self) -> None:
        """Records with different names are not equal."""
        r1 = _make_record(name="a")
        r2 = _make_record(name="b")
        assert r1 != r2

    def test_hashable(self) -> None:
        """Frozen dataclass is hashable (can be used in sets)."""
        record = _make_record()
        assert hash(record) is not None
        record_set = {record}
        assert record in record_set
