"""Tests for layout_classifier — parse classifications and group into segments."""

from __future__ import annotations

import json

import pytest

from pipeline.domain.models import LayoutClassification, SegmentLayout
from pipeline.infrastructure.adapters.layout_classifier import (
    KNOWN_LAYOUTS,
    group_into_segments,
    has_unknown_layouts,
    parse_layout_classifications,
    unknown_segments,
)


class TestParseLayoutClassifications:
    def test_parses_valid_json(self) -> None:
        raw = json.dumps(
            [
                {"timestamp": 1.0, "layout_name": "side_by_side", "confidence": 0.95},
                {"timestamp": 5.0, "layout_name": "speaker_focus", "confidence": 0.88},
            ]
        )
        result = parse_layout_classifications(raw)
        assert len(result) == 2
        assert result[0] == LayoutClassification(timestamp=1.0, layout_name="side_by_side", confidence=0.95)
        assert result[1].layout_name == "speaker_focus"

    def test_default_confidence(self) -> None:
        raw = json.dumps([{"timestamp": 0.0, "layout_name": "grid"}])
        result = parse_layout_classifications(raw)
        assert result[0].confidence == 0.0

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_layout_classifications("not-json{}")

    def test_raises_on_non_array(self) -> None:
        with pytest.raises(ValueError, match="JSON array"):
            parse_layout_classifications('{"timestamp": 1.0}')

    def test_raises_on_non_dict_element(self) -> None:
        with pytest.raises(ValueError, match="Expected dict"):
            parse_layout_classifications('["not-a-dict"]')

    def test_raises_on_missing_timestamp(self) -> None:
        raw = json.dumps([{"layout_name": "grid"}])
        with pytest.raises(KeyError):
            parse_layout_classifications(raw)

    def test_raises_on_missing_layout_name(self) -> None:
        raw = json.dumps([{"timestamp": 1.0}])
        with pytest.raises(KeyError):
            parse_layout_classifications(raw)

    def test_empty_array(self) -> None:
        result = parse_layout_classifications("[]")
        assert result == ()


class TestGroupIntoSegments:
    def test_single_classification(self) -> None:
        cls = (LayoutClassification(timestamp=10.0, layout_name="side_by_side", confidence=0.9),)
        result = group_into_segments(cls, video_duration=60.0)
        assert len(result) == 1
        assert result[0].start_seconds == 10.0
        assert result[0].end_seconds == 60.0
        assert result[0].layout_name == "side_by_side"

    def test_two_different_layouts(self) -> None:
        cls = (
            LayoutClassification(timestamp=0.0, layout_name="side_by_side", confidence=0.9),
            LayoutClassification(timestamp=30.0, layout_name="speaker_focus", confidence=0.85),
        )
        result = group_into_segments(cls, video_duration=60.0)
        assert len(result) == 2
        assert result[0] == SegmentLayout(start_seconds=0.0, end_seconds=30.0, layout_name="side_by_side")
        assert result[1] == SegmentLayout(start_seconds=30.0, end_seconds=60.0, layout_name="speaker_focus")

    def test_same_layout_merges(self) -> None:
        cls = (
            LayoutClassification(timestamp=0.0, layout_name="grid", confidence=0.8),
            LayoutClassification(timestamp=10.0, layout_name="grid", confidence=0.9),
            LayoutClassification(timestamp=20.0, layout_name="grid", confidence=0.85),
        )
        result = group_into_segments(cls, video_duration=60.0)
        assert len(result) == 1
        assert result[0].layout_name == "grid"

    def test_three_transitions(self) -> None:
        cls = (
            LayoutClassification(timestamp=0.0, layout_name="side_by_side"),
            LayoutClassification(timestamp=20.0, layout_name="speaker_focus"),
            LayoutClassification(timestamp=40.0, layout_name="grid"),
        )
        result = group_into_segments(cls, video_duration=90.0)
        assert len(result) == 3
        assert result[2].end_seconds == 90.0

    def test_unsorted_input_is_sorted(self) -> None:
        cls = (
            LayoutClassification(timestamp=30.0, layout_name="speaker_focus"),
            LayoutClassification(timestamp=0.0, layout_name="side_by_side"),
        )
        result = group_into_segments(cls, video_duration=60.0)
        assert result[0].layout_name == "side_by_side"
        assert result[1].layout_name == "speaker_focus"

    def test_empty_classifications(self) -> None:
        result = group_into_segments((), video_duration=60.0)
        assert result == ()

    def test_duplicate_timestamps_deduplicated(self) -> None:
        cls = (
            LayoutClassification(timestamp=10.0, layout_name="side_by_side"),
            LayoutClassification(timestamp=10.0, layout_name="speaker_focus"),
        )
        result = group_into_segments(cls, video_duration=60.0)
        # Second duplicate timestamp is dropped, so only one segment
        assert len(result) == 1

    def test_timestamp_beyond_duration_clamped(self) -> None:
        cls = (
            LayoutClassification(timestamp=0.0, layout_name="side_by_side"),
            LayoutClassification(timestamp=100.0, layout_name="speaker_focus"),
        )
        result = group_into_segments(cls, video_duration=60.0)
        # Timestamp 100 clamped to 60, which equals video_duration -> zero-length final segment skipped
        assert len(result) == 1
        assert result[0].end_seconds == 60.0

    def test_all_same_timestamp_returns_single_segment(self) -> None:
        cls = (
            LayoutClassification(timestamp=5.0, layout_name="grid"),
            LayoutClassification(timestamp=5.0, layout_name="grid"),
            LayoutClassification(timestamp=5.0, layout_name="side_by_side"),
        )
        result = group_into_segments(cls, video_duration=60.0)
        # All duplicates dropped except first
        assert len(result) == 1


class TestHasUnknownLayouts:
    def test_all_known(self) -> None:
        segs = (
            SegmentLayout(start_seconds=0, end_seconds=30, layout_name="side_by_side"),
            SegmentLayout(start_seconds=30, end_seconds=60, layout_name="speaker_focus"),
        )
        assert not has_unknown_layouts(segs)

    def test_one_unknown(self) -> None:
        segs = (
            SegmentLayout(start_seconds=0, end_seconds=30, layout_name="side_by_side"),
            SegmentLayout(start_seconds=30, end_seconds=60, layout_name="weird_angle"),
        )
        assert has_unknown_layouts(segs)

    def test_known_layout_set(self) -> None:
        assert "side_by_side" in KNOWN_LAYOUTS
        assert "speaker_focus" in KNOWN_LAYOUTS
        assert "grid" in KNOWN_LAYOUTS
        assert "screen_share" in KNOWN_LAYOUTS

    def test_screen_share_is_known(self) -> None:
        segs = (SegmentLayout(start_seconds=0, end_seconds=30, layout_name="screen_share"),)
        assert not has_unknown_layouts(segs)


class TestUnknownSegments:
    def test_returns_only_unknown(self) -> None:
        segs = (
            SegmentLayout(start_seconds=0, end_seconds=30, layout_name="side_by_side"),
            SegmentLayout(start_seconds=30, end_seconds=60, layout_name="new_layout"),
        )
        result = unknown_segments(segs)
        assert len(result) == 1
        assert result[0].layout_name == "new_layout"


class TestLayoutClassificationModel:
    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            LayoutClassification(timestamp=-1.0, layout_name="grid")

    def test_empty_layout_name_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            LayoutClassification(timestamp=0.0, layout_name="")

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="0.0-1.0"):
            LayoutClassification(timestamp=0.0, layout_name="grid", confidence=1.5)


class TestSegmentLayoutModel:
    def test_valid_segment(self) -> None:
        seg = SegmentLayout(start_seconds=10.0, end_seconds=70.0, layout_name="side_by_side")
        assert seg.start_seconds == 10.0
        assert seg.crop_region is None

    def test_negative_start_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            SegmentLayout(start_seconds=-1.0, end_seconds=60.0, layout_name="grid")

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >"):
            SegmentLayout(start_seconds=60.0, end_seconds=30.0, layout_name="grid")

    def test_empty_layout_name_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            SegmentLayout(start_seconds=0.0, end_seconds=60.0, layout_name="")
