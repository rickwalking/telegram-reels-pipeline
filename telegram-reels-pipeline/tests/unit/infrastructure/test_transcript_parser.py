"""Tests for transcript parser — SRT/VTT parsing and moment output validation."""

from __future__ import annotations

import json

import pytest

from pipeline.domain.errors import ValidationError
from pipeline.domain.models import MomentSelection
from pipeline.infrastructure.adapters.transcript_parser import (
    entries_to_plain_text,
    parse_moment_output,
    parse_srt,
    validate_segment_bounds,
)

_SAMPLE_SRT = """\
1
00:00:00,000 --> 00:00:05,000
Hello, welcome to the show.

2
00:00:05,500 --> 00:00:10,000
Today we're talking about AI.

3
00:00:10,500 --> 00:00:15,000
Let's dive right in.
"""

_SAMPLE_VTT = """\
WEBVTT

00:00:00.000 --> 00:00:05.000
Hello, welcome to the show.

00:00:05.500 --> 00:00:10.000
Today we're talking about AI.
"""


class TestParseSrt:
    def test_parses_standard_srt(self) -> None:
        entries = parse_srt(_SAMPLE_SRT)
        assert len(entries) == 3
        assert entries[0].text == "Hello, welcome to the show."
        assert entries[0].start_seconds == 0.0
        assert entries[0].end_seconds == 5.0

    def test_parses_vtt_format(self) -> None:
        entries = parse_srt(_SAMPLE_VTT)
        assert len(entries) == 2
        assert entries[0].text == "Hello, welcome to the show."

    def test_handles_html_tags(self) -> None:
        srt = "1\n00:00:00,000 --> 00:00:05,000\n<b>Bold text</b> and <i>italic</i>\n"
        entries = parse_srt(srt)
        assert entries[0].text == "Bold text and italic"

    def test_handles_multiline_text(self) -> None:
        srt = "1\n00:00:00,000 --> 00:00:05,000\nLine one\nLine two\n"
        entries = parse_srt(srt)
        assert entries[0].text == "Line one Line two"

    def test_handles_bom(self) -> None:
        srt = "\ufeff1\n00:00:00,000 --> 00:00:05,000\nText\n"
        entries = parse_srt(srt)
        assert len(entries) == 1

    def test_handles_empty_content(self) -> None:
        entries = parse_srt("")
        assert len(entries) == 0

    def test_calculates_timestamps_correctly(self) -> None:
        srt = "1\n01:23:45,678 --> 01:24:50,000\nText\n"
        entries = parse_srt(srt)
        assert entries[0].start_seconds == pytest.approx(5025.678)
        assert entries[0].end_seconds == pytest.approx(5090.0)

    def test_sequential_index(self) -> None:
        entries = parse_srt(_SAMPLE_SRT)
        assert [e.index for e in entries] == [1, 2, 3]


class TestEntriesToPlainText:
    def test_converts_to_timestamped_text(self) -> None:
        entries = parse_srt(_SAMPLE_SRT)
        text = entries_to_plain_text(entries)
        assert "[00:00:00] Hello, welcome to the show." in text
        assert "[00:00:05] Today we're talking about AI." in text

    def test_empty_entries(self) -> None:
        text = entries_to_plain_text(())
        assert text == ""


class TestParseMomentOutput:
    def test_parses_valid_json(self) -> None:
        data = json.dumps(
            {
                "start_seconds": 60.0,
                "end_seconds": 120.0,
                "transcript_text": "The key insight is...",
                "rationale": "Strong narrative arc with emotional peak",
                "topic_match_score": 0.85,
            }
        )
        result = parse_moment_output(data)
        assert result.start_seconds == 60.0
        assert result.end_seconds == 120.0
        assert result.rationale == "Strong narrative arc with emotional peak"
        assert result.topic_match_score == 0.85

    def test_parses_json_with_code_fences(self) -> None:
        data = '```json\n{"start_seconds": 60, "end_seconds": 120, "rationale": "Good moment"}\n```'
        result = parse_moment_output(data)
        assert result.start_seconds == 60.0

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValidationError, match="not valid JSON"):
            parse_moment_output("not json")

    def test_raises_on_missing_field(self) -> None:
        data = json.dumps({"start_seconds": 60})
        with pytest.raises(ValidationError, match="Missing required field"):
            parse_moment_output(data)

    def test_raises_on_non_object(self) -> None:
        with pytest.raises(ValidationError, match="Expected JSON object"):
            parse_moment_output("[1, 2, 3]")


class TestValidateSegmentBounds:
    def test_valid_segment(self) -> None:
        selection = MomentSelection(
            start_seconds=60.0,
            end_seconds=120.0,
            transcript_text="text",
            rationale="reason",
        )
        validate_segment_bounds(selection, video_duration=3600.0)

    def test_start_exceeds_duration(self) -> None:
        selection = MomentSelection(
            start_seconds=60.0,
            end_seconds=120.0,
            transcript_text="text",
            rationale="reason",
        )
        with pytest.raises(ValidationError, match="start.*exceeds"):
            validate_segment_bounds(selection, video_duration=50.0)

    def test_end_exceeds_duration(self) -> None:
        selection = MomentSelection(
            start_seconds=60.0,
            end_seconds=120.0,
            transcript_text="text",
            rationale="reason",
        )
        with pytest.raises(ValidationError, match="end.*exceeds"):
            validate_segment_bounds(selection, video_duration=100.0)


class TestMomentSelectionModel:
    def test_valid_selection(self) -> None:
        m = MomentSelection(
            start_seconds=60.0,
            end_seconds=120.0,
            transcript_text="Some text",
            rationale="Strong emotional peak",
        )
        assert m.duration_seconds == 60.0

    def test_rejects_negative_start(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            MomentSelection(start_seconds=-1.0, end_seconds=60.0, transcript_text="t", rationale="r")

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(ValueError, match="must be >"):
            MomentSelection(start_seconds=120.0, end_seconds=60.0, transcript_text="t", rationale="r")

    def test_rejects_too_short(self) -> None:
        with pytest.raises(ValueError, match="30-120s"):
            MomentSelection(start_seconds=0.0, end_seconds=10.0, transcript_text="t", rationale="r")

    def test_rejects_too_long(self) -> None:
        with pytest.raises(ValueError, match="30-120s"):
            MomentSelection(start_seconds=0.0, end_seconds=200.0, transcript_text="t", rationale="r")

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(ValueError, match="rationale"):
            MomentSelection(start_seconds=0.0, end_seconds=60.0, transcript_text="t", rationale="")

    def test_rejects_invalid_topic_score(self) -> None:
        with pytest.raises(ValueError, match="topic_match_score"):
            MomentSelection(
                start_seconds=0.0, end_seconds=60.0, transcript_text="t", rationale="r", topic_match_score=1.5
            )

    def test_duration_property(self) -> None:
        m = MomentSelection(start_seconds=30.0, end_seconds=90.0, transcript_text="t", rationale="r")
        assert m.duration_seconds == 60.0
