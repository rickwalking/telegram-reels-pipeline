"""Tests for revision_classifier — parsing AI revision classification output."""

from __future__ import annotations

import json

import pytest

from pipeline.application.revision_router import (
    parse_extra_seconds,
    parse_revision_classification,
    parse_timestamp_hint,
)
from pipeline.domain.enums import RevisionType


class TestParseRevisionClassification:
    def test_valid_extend_moment(self) -> None:
        raw = json.dumps({
            "revision_type": "extend_moment",
            "confidence": 0.95,
            "reasoning": "User wants more time",
        })
        rev_type, confidence = parse_revision_classification(raw)
        assert rev_type == RevisionType.EXTEND_MOMENT
        assert confidence == pytest.approx(0.95)

    def test_valid_fix_framing(self) -> None:
        raw = json.dumps({"revision_type": "fix_framing", "confidence": 0.8})
        rev_type, confidence = parse_revision_classification(raw)
        assert rev_type == RevisionType.FIX_FRAMING
        assert confidence == pytest.approx(0.8)

    def test_valid_different_moment(self) -> None:
        raw = json.dumps({"revision_type": "different_moment", "confidence": 0.7})
        rev_type, _ = parse_revision_classification(raw)
        assert rev_type == RevisionType.DIFFERENT_MOMENT

    def test_valid_add_context(self) -> None:
        raw = json.dumps({"revision_type": "add_context", "confidence": 0.9})
        rev_type, _ = parse_revision_classification(raw)
        assert rev_type == RevisionType.ADD_CONTEXT

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_revision_classification("not json {{{")

    def test_non_object_raises(self) -> None:
        with pytest.raises(ValueError, match="Expected a JSON object"):
            parse_revision_classification(json.dumps([1, 2]))

    def test_unknown_type_raises(self) -> None:
        raw = json.dumps({"revision_type": "delete_video", "confidence": 0.9})
        with pytest.raises(ValueError, match="Unknown revision_type"):
            parse_revision_classification(raw)

    def test_missing_type_raises(self) -> None:
        raw = json.dumps({"confidence": 0.9})
        with pytest.raises(ValueError, match="Unknown revision_type"):
            parse_revision_classification(raw)

    def test_confidence_out_of_range_raises(self) -> None:
        raw = json.dumps({"revision_type": "fix_framing", "confidence": 1.5})
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            parse_revision_classification(raw)

    def test_confidence_not_number_raises(self) -> None:
        raw = json.dumps({"revision_type": "fix_framing", "confidence": "high"})
        with pytest.raises(ValueError, match="confidence must be a number"):
            parse_revision_classification(raw)

    def test_zero_confidence_valid(self) -> None:
        raw = json.dumps({"revision_type": "fix_framing", "confidence": 0.0})
        _, confidence = parse_revision_classification(raw)
        assert confidence == 0.0

    def test_default_confidence_zero(self) -> None:
        raw = json.dumps({"revision_type": "fix_framing"})
        _, confidence = parse_revision_classification(raw)
        assert confidence == 0.0


class TestParseTimestampHint:
    def test_present_value(self) -> None:
        raw = json.dumps({"timestamp_hint": 2700.0})
        assert parse_timestamp_hint(raw) == pytest.approx(2700.0)

    def test_integer_value(self) -> None:
        raw = json.dumps({"timestamp_hint": 300})
        assert parse_timestamp_hint(raw) == pytest.approx(300.0)

    def test_null_value(self) -> None:
        raw = json.dumps({"timestamp_hint": None})
        assert parse_timestamp_hint(raw) is None

    def test_missing_key(self) -> None:
        raw = json.dumps({"other": "stuff"})
        assert parse_timestamp_hint(raw) is None

    def test_invalid_json(self) -> None:
        assert parse_timestamp_hint("not json") is None

    def test_non_numeric_value(self) -> None:
        raw = json.dumps({"timestamp_hint": "around 45 minutes"})
        assert parse_timestamp_hint(raw) is None


class TestParseExtraSeconds:
    def test_present_value(self) -> None:
        raw = json.dumps({"extra_seconds": 15.0})
        assert parse_extra_seconds(raw) == pytest.approx(15.0)

    def test_integer_value(self) -> None:
        raw = json.dumps({"extra_seconds": 10})
        assert parse_extra_seconds(raw) == pytest.approx(10.0)

    def test_missing_defaults_zero(self) -> None:
        raw = json.dumps({"other": "stuff"})
        assert parse_extra_seconds(raw) == 0.0

    def test_invalid_json_defaults_zero(self) -> None:
        assert parse_extra_seconds("bad json") == 0.0

    def test_negative_clamped_to_zero(self) -> None:
        raw = json.dumps({"extra_seconds": -5.0})
        assert parse_extra_seconds(raw) == 0.0

    def test_non_numeric_defaults_zero(self) -> None:
        raw = json.dumps({"extra_seconds": "fifteen"})
        assert parse_extra_seconds(raw) == 0.0
