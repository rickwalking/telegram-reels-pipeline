"""Parse structured directive fields from router-output.json into CreativeDirectives."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pipeline.domain.directives import (
    CreativeDirectives,
    DocumentaryClip,
    NarrativeOverride,
    OverlayImage,
    TransitionPreference,
)

logger = logging.getLogger(__name__)


def parse_directives(router_output: Mapping[str, Any]) -> CreativeDirectives:
    """Parse router output dict into typed CreativeDirectives.

    Gracefully handles malformed or missing fields -- returns empty
    directives rather than raising. Logs warnings for invalid entries.
    """
    raw_instructions = str(router_output.get("instructions", ""))

    overlay_images = _parse_overlay_images(router_output.get("overlay_images", []))
    documentary_clips = _parse_documentary_clips(router_output.get("documentary_clips", []))
    transition_preferences = _parse_transitions(router_output.get("transition_preferences", []))
    narrative_overrides = _parse_narrative_overrides(router_output.get("narrative_overrides", []))

    return CreativeDirectives(
        overlay_images=overlay_images,
        documentary_clips=documentary_clips,
        transition_preferences=transition_preferences,
        narrative_overrides=narrative_overrides,
        raw_instructions=raw_instructions,
    )


def _parse_overlay_images(raw: Any) -> tuple[OverlayImage, ...]:
    """Parse overlay_images list from router output."""
    if not isinstance(raw, list):
        return ()
    results: list[OverlayImage] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            logger.warning("overlay_images[%d]: expected dict, got %s", i, type(entry).__name__)
            continue
        try:
            results.append(
                OverlayImage(
                    path=str(entry.get("path", "")),
                    timestamp_s=float(entry.get("timestamp_s", 0)),
                    duration_s=float(entry.get("duration_s", 0)),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("overlay_images[%d]: skipped -- %s", i, exc)
    return tuple(results)


def _parse_documentary_clips(raw: Any) -> tuple[DocumentaryClip, ...]:
    """Parse documentary_clips list from router output."""
    if not isinstance(raw, list):
        return ()
    results: list[DocumentaryClip] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            logger.warning("documentary_clips[%d]: expected dict, got %s", i, type(entry).__name__)
            continue
        try:
            results.append(
                DocumentaryClip(
                    path_or_query=str(entry.get("path_or_query", "")),
                    placement_hint=str(entry.get("placement_hint", "")),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("documentary_clips[%d]: skipped -- %s", i, exc)
    return tuple(results)


def _parse_transitions(raw: Any) -> tuple[TransitionPreference, ...]:
    """Parse transition_preferences list from router output."""
    if not isinstance(raw, list):
        return ()
    results: list[TransitionPreference] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            logger.warning("transition_preferences[%d]: expected dict, got %s", i, type(entry).__name__)
            continue
        try:
            results.append(
                TransitionPreference(
                    effect_type=str(entry.get("effect_type", "")),
                    timing_s=float(entry.get("timing_s", 0)),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("transition_preferences[%d]: skipped -- %s", i, exc)
    return tuple(results)


def _parse_narrative_overrides(raw: Any) -> tuple[NarrativeOverride, ...]:
    """Parse narrative_overrides list from router output."""
    if not isinstance(raw, list):
        return ()
    results: list[NarrativeOverride] = []
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            logger.warning("narrative_overrides[%d]: expected dict, got %s", i, type(entry).__name__)
            continue
        try:
            results.append(
                NarrativeOverride(
                    tone=str(entry.get("tone", "")),
                    structure=str(entry.get("structure", "")),
                    pacing=str(entry.get("pacing", "")),
                    arc_changes=str(entry.get("arc_changes", "")),
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("narrative_overrides[%d]: skipped -- %s", i, exc)
    return tuple(results)
