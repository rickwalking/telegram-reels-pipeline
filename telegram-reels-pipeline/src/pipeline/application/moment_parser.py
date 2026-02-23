"""Parser for multi-moment narrative plans from agent JSON output."""

from __future__ import annotations

import logging
from typing import Any

from pipeline.domain.enums import NarrativeRole
from pipeline.domain.models import NARRATIVE_ROLE_ORDER, NarrativeMoment, NarrativePlan

logger = logging.getLogger(__name__)


def _role_sort_key(role: NarrativeRole) -> int:
    """Return sort index for narrative role ordering."""
    try:
        return NARRATIVE_ROLE_ORDER.index(role)
    except ValueError:
        return len(NARRATIVE_ROLE_ORDER)


def _parse_role(raw: str) -> NarrativeRole | None:
    """Parse a raw role string to NarrativeRole, returning None on failure."""
    try:
        return NarrativeRole(raw.lower().strip())
    except (ValueError, AttributeError):
        return None


def _parse_moment(raw: dict[str, Any]) -> NarrativeMoment | None:
    """Parse a single moment dict into a NarrativeMoment, returning None on failure."""
    try:
        start = float(raw["start_seconds"])
        end = float(raw["end_seconds"])
        role_str = raw.get("role", "")
        role = _parse_role(str(role_str))
        if role is None:
            return None
        excerpt = str(raw.get("transcript_excerpt", raw.get("transcript_text", "")))
        if not excerpt:
            return None
        return NarrativeMoment(
            start_seconds=start,
            end_seconds=end,
            role=role,
            transcript_excerpt=excerpt,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _build_single_moment_fallback(data: dict[str, Any], target_duration: float) -> NarrativePlan | None:
    """Build a single-moment NarrativePlan from legacy top-level fields."""
    try:
        start = float(data["start_seconds"])
        end = float(data["end_seconds"])
        excerpt = str(data.get("transcript_text", data.get("transcript_excerpt", "")))
        if not excerpt:
            excerpt = "single moment fallback"
        moment = NarrativeMoment(
            start_seconds=start,
            end_seconds=end,
            role=NarrativeRole.CORE,
            transcript_excerpt=excerpt,
        )
        return NarrativePlan(moments=(moment,), target_duration_seconds=target_duration)
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning("Failed to build single-moment fallback: %s", exc)
        return None


def parse_narrative_plan(data: dict[str, Any], target_duration: float = 90.0) -> NarrativePlan | None:
    """Parse a moment-selection.json dict into a NarrativePlan.

    Three paths:
    1. Multi-moment: ``data["moments"]`` array with 2+ items → full NarrativePlan
    2. Legacy single: top-level ``start_seconds``/``end_seconds`` → single CORE moment
    3. Malformed fallback: ``moments`` array parse fails → fall back to single-moment

    Returns None only if all paths fail (no usable data at all).
    """
    raw_moments = data.get("moments")

    if isinstance(raw_moments, list) and len(raw_moments) >= 2:
        parsed: list[NarrativeMoment] = []
        for raw in raw_moments:
            if not isinstance(raw, dict):
                continue
            moment = _parse_moment(raw)
            if moment is not None:
                parsed.append(moment)

        if parsed:
            # Sort by narrative role order
            parsed.sort(key=lambda m: _role_sort_key(m.role))

            try:
                return NarrativePlan(
                    moments=tuple(parsed),
                    target_duration_seconds=target_duration,
                )
            except ValueError as exc:
                logger.warning("Multi-moment NarrativePlan validation failed: %s — falling back to single-moment", exc)

    # Fallback: single-moment from top-level fields
    return _build_single_moment_fallback(data, target_duration)
