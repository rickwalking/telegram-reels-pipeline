"""Tests for VTT speaker timeline parser."""

from __future__ import annotations

# Import directly since scripts/ is not a package — use importlib or subprocess
import importlib.util
import sys
from pathlib import Path

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "parse_vtt_speakers.py"
_spec = importlib.util.spec_from_file_location("parse_vtt_speakers", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["parse_vtt_speakers"] = _mod
_spec.loader.exec_module(_mod)

parse_vtt_speakers = _mod.parse_vtt_speakers
MIN_SEGMENT_DURATION_S = _mod.MIN_SEGMENT_DURATION_S


def _write_vtt(tmp_path: Path, content: str) -> Path:
    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text(content, encoding="utf-8")
    return vtt_file


# -- Minimal VTT with speaker markers ---

_VTT_TWO_SPEAKERS = """\
WEBVTT

00:32:45.000 --> 00:32:50.000
&gt;&gt; Hello, welcome to the show.

00:32:50.000 --> 00:32:55.000
&gt;&gt; Thanks for having me.

00:32:58.000 --> 00:33:03.000
&gt;&gt; Let's talk about topic.

00:33:10.000 --> 00:33:15.000
&gt;&gt; Sure, that sounds great.
"""

_VTT_NO_MARKERS = """\
WEBVTT

00:32:45.000 --> 00:32:50.000
Hello, welcome to the show.

00:32:50.000 --> 00:32:55.000
Thanks for having me.
"""

_VTT_RAPID_CHANGES = """\
WEBVTT

00:00:01.000 --> 00:00:02.000
&gt;&gt; First speaker.

00:00:02.500 --> 00:00:03.500
&gt;&gt; Second speaker.

00:00:03.800 --> 00:00:04.800
&gt;&gt; Back to first.

00:00:05.000 --> 00:00:06.000
&gt;&gt; Second again.

00:00:10.000 --> 00:00:11.000
&gt;&gt; Later change.
"""

_VTT_SINGLE_SPEAKER = """\
WEBVTT

00:10:00.000 --> 00:10:05.000
&gt;&gt; This is a monologue.
"""

_VTT_RAW_MARKERS = """\
WEBVTT

00:05:00.000 --> 00:05:05.000
>> Raw marker test.

00:05:10.000 --> 00:05:15.000
>> Second raw marker.
"""


class TestParseVttSpeakers:
    def test_two_speakers_detected(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file)

        assert result["speakers_detected"] == 2
        assert result["source"] == "vtt_markers"
        assert result["confidence"] == "medium"
        assert len(result["timeline"]) > 0

    def test_speaker_alternation(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file)

        timeline = result["timeline"]
        speakers = [entry["speaker"] for entry in timeline]
        # Speakers alternate A, B, A, B...
        for i in range(1, len(speakers)):
            assert speakers[i] != speakers[i - 1], f"Speaker did not alternate at index {i}"

    def test_no_markers_returns_none_confidence(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_NO_MARKERS)
        result = parse_vtt_speakers(vtt_file)

        assert result["speakers_detected"] == 0
        assert result["timeline"] == []
        assert result["confidence"] == "none"

    def test_empty_file(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, "")
        result = parse_vtt_speakers(vtt_file)

        assert result["speakers_detected"] == 0
        assert result["confidence"] == "none"

    def test_missing_file(self, tmp_path: Path) -> None:
        result = parse_vtt_speakers(tmp_path / "nonexistent.vtt")

        assert result["speakers_detected"] == 0
        assert result["confidence"] == "none"
        assert "error" in result

    def test_range_filtering_start_s(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file, start_s=1978.0)

        timeline = result["timeline"]
        for entry in timeline:
            assert entry["start_s"] >= 1978.0 or entry["end_s"] >= 1978.0

    def test_range_filtering_end_s(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file, end_s=1970.0)

        timeline = result["timeline"]
        for entry in timeline:
            assert entry["end_s"] <= 1970.0

    def test_range_filtering_excludes_all(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        # Filter to a range with no markers
        result = parse_vtt_speakers(vtt_file, start_s=99999.0, end_s=99999.5)

        assert result["speakers_detected"] == 0
        assert result["timeline"] == []

    def test_rapid_changes_debounced(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_RAPID_CHANGES)
        result = parse_vtt_speakers(vtt_file)

        timeline = result["timeline"]
        # Debouncing should merge changes < MIN_SEGMENT_DURATION_S apart
        for entry in timeline:
            duration = entry["end_s"] - entry["start_s"]
            assert duration >= MIN_SEGMENT_DURATION_S, (
                f"Sub-segment duration {duration}s is less than minimum {MIN_SEGMENT_DURATION_S}s"
            )

    def test_single_speaker_content(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_SINGLE_SPEAKER)
        result = parse_vtt_speakers(vtt_file)

        # Single marker means single speaker
        assert result["confidence"] == "low"

    def test_raw_markers_detected(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_RAW_MARKERS)
        result = parse_vtt_speakers(vtt_file)

        assert result["speakers_detected"] >= 1
        assert len(result["timeline"]) > 0

    def test_timeline_timestamps_are_monotonic(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file)

        timeline = result["timeline"]
        for i in range(1, len(timeline)):
            assert timeline[i]["start_s"] >= timeline[i - 1]["start_s"]

    def test_result_structure(self, tmp_path: Path) -> None:
        vtt_file = _write_vtt(tmp_path, _VTT_TWO_SPEAKERS)
        result = parse_vtt_speakers(vtt_file)

        assert "speakers_detected" in result
        assert "timeline" in result
        assert "source" in result
        assert "confidence" in result
        assert isinstance(result["timeline"], list)
