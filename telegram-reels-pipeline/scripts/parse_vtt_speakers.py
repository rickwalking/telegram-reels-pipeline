"""Parse YouTube VTT subtitles for speaker change markers (>>) to build a speaker timeline.

Produces speaker-timeline.json with speaker turn boundaries for intelligent crop decisions.

Usage::

    python scripts/parse_vtt_speakers.py <vtt_file> [--start-s N] [--end-s N] [--output path]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# VTT timestamp format: HH:MM:SS.mmm
_TS_PATTERN = re.compile(r"(\d{2}):(\d{2}):(\d{2})\.(\d{3})")

# Speaker change marker (HTML-encoded >> or raw >>)
_SPEAKER_MARKER = re.compile(r"(?:&gt;&gt;|>>)\s*")

# Minimum sub-segment duration to avoid jarring rapid cuts
MIN_SEGMENT_DURATION_S = 2.0


def _parse_timestamp(ts: str) -> float | None:
    """Convert VTT timestamp (HH:MM:SS.mmm) to seconds. Returns None on parse failure."""
    m = _TS_PATTERN.match(ts.strip())
    if not m:
        return None
    h, mins, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return h * 3600 + mins * 60 + s + ms / 1000.0


def _extract_cue_timestamp(line: str) -> float | None:
    """Extract the start timestamp from a VTT cue timing line (e.g., '00:32:45.000 --> 00:32:50.000')."""
    if "-->" not in line:
        return None
    parts = line.split("-->")
    if len(parts) < 2:
        return None
    ts = _parse_timestamp(parts[0].strip())
    return ts  # Returns None for invalid timestamps instead of 0.0


def _empty_result(**extra: object) -> dict[str, object]:
    """Return an empty speaker timeline result."""
    result: dict[str, object] = {
        "speakers_detected": 0,
        "timeline": [],
        "source": "vtt_markers",
        "confidence": "none",
    }
    result.update(extra)
    return result


def _extract_raw_changes(text: str) -> list[float]:
    """Scan VTT text for speaker change marker timestamps."""
    raw_changes: list[float] = []
    current_timestamp: float | None = None

    for line in text.splitlines():
        line_stripped = line.strip()
        ts = _extract_cue_timestamp(line_stripped)
        if ts is not None:
            current_timestamp = ts
            continue
        if current_timestamp is not None and _SPEAKER_MARKER.search(line_stripped):
            raw_changes.append(current_timestamp)
            current_timestamp = None  # Only count first marker per cue

    return raw_changes


def _filter_and_debounce(
    changes: list[float],
    start_s: float | None,
    end_s: float | None,
) -> list[float]:
    """Filter changes to moment range and debounce rapid changes."""
    if start_s is not None:
        changes = [t for t in changes if t >= start_s]
    if end_s is not None:
        changes = [t for t in changes if t <= end_s]
    if not changes:
        return []

    debounced: list[float] = [changes[0]]
    for t in changes[1:]:
        if t - debounced[-1] >= MIN_SEGMENT_DURATION_S:
            debounced.append(t)
    return debounced


def _build_timeline(
    debounced: list[float],
    start_s: float | None,
    end_s: float | None,
) -> list[dict[str, object]]:
    """Build speaker timeline from debounced change points."""
    effective_end = end_s if end_s is not None else debounced[-1] + MIN_SEGMENT_DURATION_S
    timeline: list[dict[str, object]] = []
    speakers = ("A", "B")

    for i, _change_t in enumerate(debounced):
        speaker = speakers[i % 2]
        seg_start = debounced[i]
        seg_end = debounced[i + 1] if i + 1 < len(debounced) else effective_end

        if start_s is not None:
            seg_start = max(seg_start, start_s)
        if end_s is not None:
            seg_end = min(seg_end, end_s)

        if seg_end - seg_start >= MIN_SEGMENT_DURATION_S:
            timeline.append({
                "speaker": speaker,
                "start_s": round(seg_start, 3),
                "end_s": round(seg_end, 3),
            })
    return timeline


def parse_vtt_speakers(
    vtt_path: Path,
    start_s: float | None = None,
    end_s: float | None = None,
) -> dict[str, object]:
    """Parse VTT file for speaker change markers and build a speaker timeline.

    Args:
        vtt_path: Path to VTT subtitle file.
        start_s: Start of moment range in seconds (filters timeline).
        end_s: End of moment range in seconds (filters timeline).

    Returns:
        Dictionary with speakers_detected, timeline, source, and confidence.
    """
    if not vtt_path.exists():
        return _empty_result(error=f"VTT file not found: {vtt_path}")

    text = vtt_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return _empty_result()

    raw_changes = _extract_raw_changes(text)
    if not raw_changes:
        return _empty_result()

    changes = sorted(set(raw_changes))
    debounced = _filter_and_debounce(changes, start_s, end_s)
    if not debounced:
        return _empty_result()

    timeline = _build_timeline(debounced, start_s, end_s)
    unique_speakers = len({entry["speaker"] for entry in timeline})

    return {
        "speakers_detected": unique_speakers,
        "timeline": timeline,
        "source": "vtt_markers",
        "confidence": "medium" if unique_speakers >= 2 else "low",
    }


def _atomic_write_json(data: object, output_path: Path) -> None:
    """Write JSON atomically (write-to-tmp + rename)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, output_path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse VTT subtitles for speaker change markers")
    parser.add_argument("vtt_file", type=Path, help="Path to VTT subtitle file")
    parser.add_argument("--start-s", type=float, default=None, help="Start of moment range (seconds)")
    parser.add_argument("--end-s", type=float, default=None, help="End of moment range (seconds)")
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: stdout)")
    args = parser.parse_args()

    result = parse_vtt_speakers(args.vtt_file, start_s=args.start_s, end_s=args.end_s)

    if args.output:
        _atomic_write_json(result, args.output)
        print(f"Speaker timeline written to {args.output}", file=sys.stderr)
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
