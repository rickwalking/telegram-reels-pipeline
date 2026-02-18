"""Layout classifier — parse AI agent output into domain layout models."""

from __future__ import annotations

import json
import logging

from pipeline.domain.models import LayoutClassification, SegmentLayout

logger = logging.getLogger(__name__)

# Known layout types that have predefined crop strategies
KNOWN_LAYOUTS: frozenset[str] = frozenset({
    "side_by_side",
    "speaker_focus",
    "grid",
    "screen_share",
})


def parse_layout_classifications(raw: str) -> tuple[LayoutClassification, ...]:
    """Parse JSON array output from layout detective agent.

    Expected format:
    [
        {"timestamp": 10.5, "layout_name": "side_by_side", "confidence": 0.95},
        ...
    ]
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in layout classification output: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of classifications")

    results: list[LayoutClassification] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Expected dict in classification array, got {type(item).__name__}")
        results.append(
            LayoutClassification(
                timestamp=float(item["timestamp"]),
                layout_name=str(item["layout_name"]),
                confidence=float(item.get("confidence", 0.0)),
            )
        )

    return tuple(results)


def group_into_segments(
    classifications: tuple[LayoutClassification, ...],
    video_duration: float,
) -> tuple[SegmentLayout, ...]:
    """Group consecutive frames with the same layout into contiguous segments.

    Classifications are sorted by timestamp, clamped to [0, video_duration],
    and deduplicated. Adjacent frames with the same layout_name are merged
    into a single SegmentLayout. Zero-length segments are skipped.
    """
    if not classifications:
        return ()

    # Sort, clamp to valid range, and deduplicate timestamps
    sorted_cls = sorted(classifications, key=lambda c: c.timestamp)
    clamped: list[LayoutClassification] = []
    seen_timestamps: set[float] = set()
    for cls in sorted_cls:
        ts = max(0.0, min(cls.timestamp, video_duration))
        if ts in seen_timestamps:
            continue
        seen_timestamps.add(ts)
        clamped.append(LayoutClassification(timestamp=ts, layout_name=cls.layout_name, confidence=cls.confidence))

    if not clamped:
        return ()

    segments: list[SegmentLayout] = []
    current_layout = clamped[0].layout_name
    start = clamped[0].timestamp

    for i in range(1, len(clamped)):
        if clamped[i].layout_name != current_layout:
            end = clamped[i].timestamp
            if end > start:
                segments.append(
                    SegmentLayout(start_seconds=start, end_seconds=end, layout_name=current_layout)
                )
            current_layout = clamped[i].layout_name
            start = clamped[i].timestamp

    # Last segment extends to video end (skip if zero-length)
    if video_duration > start:
        segments.append(
            SegmentLayout(start_seconds=start, end_seconds=video_duration, layout_name=current_layout)
        )

    return tuple(segments)


def has_unknown_layouts(segments: tuple[SegmentLayout, ...]) -> bool:
    """Check if any segment has an unknown layout requiring escalation."""
    return any(seg.layout_name not in KNOWN_LAYOUTS for seg in segments)


def unknown_segments(segments: tuple[SegmentLayout, ...]) -> tuple[SegmentLayout, ...]:
    """Return only segments with unknown layouts."""
    return tuple(seg for seg in segments if seg.layout_name not in KNOWN_LAYOUTS)
