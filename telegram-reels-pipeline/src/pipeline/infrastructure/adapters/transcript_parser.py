"""Transcript parser — parse SRT/VTT subtitle files into structured segments."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pipeline.domain.errors import ValidationError
from pipeline.domain.models import MomentSelection

# SRT timestamp pattern: 00:01:23,456
_SRT_TS_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})")

# SRT block separator
_SRT_BLOCK_RE = re.compile(r"\n\n+")

# Minimum/maximum segment duration
MIN_SEGMENT_SECONDS: float = 30.0
MAX_SEGMENT_SECONDS: float = 120.0


@dataclass(frozen=True)
class SubtitleEntry:
    """A single subtitle entry with timing and text."""

    index: int
    start_seconds: float
    end_seconds: float
    text: str


def parse_srt(content: str) -> tuple[SubtitleEntry, ...]:
    """Parse SRT subtitle content into a sequence of SubtitleEntry objects.

    Handles both SRT (comma separator) and VTT (dot separator) timestamp formats.
    Strips HTML tags and formatting directives.
    """
    # Strip BOM and normalize line endings
    content = content.lstrip("\ufeff").replace("\r\n", "\n").strip()

    # Skip VTT header if present
    if content.startswith("WEBVTT"):
        content = re.sub(r"^WEBVTT[^\n]*\n+", "", content)

    blocks = _SRT_BLOCK_RE.split(content)
    entries: list[SubtitleEntry] = []
    idx = 0

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = block.split("\n")
        if len(lines) < 2:
            continue

        # Find the timestamp line (may or may not have an index line before it)
        ts_line_idx = 0
        if "-->" not in lines[0]:
            ts_line_idx = 1
            if len(lines) < 3 or "-->" not in lines[1]:
                continue

        ts_line = lines[ts_line_idx]
        timestamps = _SRT_TS_RE.findall(ts_line)
        if len(timestamps) < 2:
            continue

        start = _ts_to_seconds(timestamps[0])
        end = _ts_to_seconds(timestamps[1])

        # Text is everything after the timestamp line
        text_lines = lines[ts_line_idx + 1 :]
        text = " ".join(_strip_tags(line) for line in text_lines if line.strip())
        text = text.strip()

        if text:
            idx += 1
            entries.append(SubtitleEntry(index=idx, start_seconds=start, end_seconds=end, text=text))

    return tuple(entries)


def entries_to_plain_text(entries: tuple[SubtitleEntry, ...]) -> str:
    """Convert subtitle entries to plain text with timestamp markers."""
    parts: list[str] = []
    for entry in entries:
        ts = _seconds_to_ts(entry.start_seconds)
        parts.append(f"[{ts}] {entry.text}")
    return "\n".join(parts)


def parse_moment_output(raw_json: str) -> MomentSelection:
    """Parse the agent's moment selection JSON output into a MomentSelection model.

    Expected format:
    {
        "start_seconds": 123.4,
        "end_seconds": 189.2,
        "transcript_text": "...",
        "rationale": "...",
        "topic_match_score": 0.85
    }
    """
    # Strip markdown code fences if present
    cleaned = raw_json.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Moment selection output is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError(f"Expected JSON object, got {type(data).__name__}")

    try:
        return MomentSelection(
            start_seconds=float(data["start_seconds"]),
            end_seconds=float(data["end_seconds"]),
            transcript_text=str(data.get("transcript_text", "")),
            rationale=str(data["rationale"]),
            topic_match_score=float(data.get("topic_match_score", 0.0)),
        )
    except KeyError as exc:
        raise ValidationError(f"Missing required field in moment selection: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid moment selection values: {exc}") from exc


def validate_segment_bounds(
    selection: MomentSelection,
    video_duration: float,
) -> None:
    """Validate that the selected segment falls within the video duration.

    Raises ValidationError if bounds are invalid.
    """
    if selection.start_seconds >= video_duration:
        raise ValidationError(f"Segment start ({selection.start_seconds}s) exceeds video duration ({video_duration}s)")
    if selection.end_seconds > video_duration + 1.0:
        raise ValidationError(f"Segment end ({selection.end_seconds}s) exceeds video duration ({video_duration}s)")


def _ts_to_seconds(parts: tuple[str, ...]) -> float:
    """Convert (HH, MM, SS, ms) tuple to seconds."""
    h, m, s, ms = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return h * 3600 + m * 60 + s + ms / 1000


def _seconds_to_ts(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _strip_tags(text: str) -> str:
    """Remove HTML/SRT tags like <b>, <i>, <font>."""
    return re.sub(r"<[^>]+>", "", text)
