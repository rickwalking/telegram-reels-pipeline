"""B-roll placement resolver — maps Veo3 clips to timeline positions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pipeline.domain.models import BrollPlacement

logger = logging.getLogger(__name__)

# Minimum Jaccard similarity for a broll anchor match to be accepted.
_MIN_MATCH_CONFIDENCE: float = 0.3


class BrollPlacer:
    """Resolve B-roll clip placements on the final reel timeline.

    Reads completed Veo3 clips from ``veo3/jobs.json`` and maps each to a
    timeline position based on its variant type:

    - **intro**: placed at the start of the reel (t=0).
    - **outro**: placed at the end of the reel.
    - **transition**: placed at the boundary between narrative moments.
    - **broll**: matched to a segment via keyword overlap of its narrative anchor.
    """

    def resolve_placements(
        self,
        workspace: Path,
        segments: list[dict[str, object]],
        total_duration_s: float,
    ) -> tuple[BrollPlacement, ...]:
        """Resolve insertion points for all completed Veo3 clips.

        Args:
            workspace: Pipeline run workspace directory.
            segments: List of segment dicts (each with ``start_s``, ``end_s``,
                and optionally ``transcript_text``).
            total_duration_s: Total reel duration in seconds.

        Returns:
            Tuple of :class:`BrollPlacement` sorted by ``insertion_point_s``.
        """
        completed = self._get_completed_clips(workspace)
        if not completed:
            return ()

        anchors = self._load_narrative_anchors(workspace)
        boundaries = self._load_segment_boundaries(workspace)

        placements: list[BrollPlacement] = []
        for clip in completed:
            variant = str(clip.get("variant", ""))
            video_path = str(clip.get("video_path", ""))
            prompt_text = str(clip.get("prompt", ""))

            anchor_text = anchors.get(variant, "")
            duration = self._estimate_clip_duration(clip)

            if variant == "intro":
                placements.append(
                    BrollPlacement(
                        variant=variant,
                        clip_path=video_path,
                        insertion_point_s=0.0,
                        duration_s=duration,
                        narrative_anchor=anchor_text,
                        match_confidence=1.0,
                    )
                )

            elif variant == "outro":
                insertion = max(0.0, total_duration_s - duration)
                placements.append(
                    BrollPlacement(
                        variant=variant,
                        clip_path=video_path,
                        insertion_point_s=insertion,
                        duration_s=duration,
                        narrative_anchor=anchor_text,
                        match_confidence=1.0,
                    )
                )

            elif variant == "transition":
                insertion = self._resolve_transition_point(boundaries, total_duration_s, duration)
                placements.append(
                    BrollPlacement(
                        variant=variant,
                        clip_path=video_path,
                        insertion_point_s=insertion,
                        duration_s=duration,
                        narrative_anchor=anchor_text,
                        match_confidence=1.0,
                    )
                )

            elif variant == "broll":
                if not segments:
                    logger.warning("No segments available for broll anchor matching — skipping clip %s", video_path)
                    continue
                seg_idx, confidence = self._match_anchor(anchor_text or prompt_text, segments)
                if confidence < _MIN_MATCH_CONFIDENCE:
                    logger.warning(
                        "Broll anchor match too weak (%.2f < %.2f) for clip %s — skipping",
                        confidence,
                        _MIN_MATCH_CONFIDENCE,
                        video_path,
                    )
                    continue
                seg = segments[seg_idx]
                seg_start = float(str(seg.get("start_s", 0.0) or 0.0))
                seg_end = float(str(seg.get("end_s", seg_start) or seg_start))
                midpoint = seg_start + (seg_end - seg_start) / 2.0
                insertion = max(0.0, midpoint - duration / 2.0)
                placements.append(
                    BrollPlacement(
                        variant=variant,
                        clip_path=video_path,
                        insertion_point_s=insertion,
                        duration_s=duration,
                        narrative_anchor=anchor_text,
                        match_confidence=confidence,
                    )
                )

            else:
                logger.warning("Unknown variant '%s' — skipping clip %s", variant, video_path)

        placements.sort(key=lambda p: p.insertion_point_s)
        return tuple(placements)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_completed_clips(workspace: Path) -> list[dict[str, object]]:
        """Read veo3/jobs.json and return completed clips with a video_path."""
        jobs_path = workspace / "veo3" / "jobs.json"
        try:
            raw = jobs_path.read_text()
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            logger.debug("Cannot read veo3/jobs.json: %s", exc)
            return []

        result: list[dict[str, object]] = []
        for entry in data.get("jobs", []):
            if entry.get("status") == "completed" and entry.get("video_path"):
                result.append(entry)
        return result

    @staticmethod
    def _load_narrative_anchors(workspace: Path) -> dict[str, str]:
        """Load narrative_anchor per variant from publishing-assets.json."""
        assets_path = workspace / "publishing-assets.json"
        try:
            raw = assets_path.read_text()
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

        anchors: dict[str, str] = {}
        for prompt in data.get("veo3_prompts", []):
            variant = str(prompt.get("variant", ""))
            anchor = str(prompt.get("narrative_anchor", ""))
            if variant and anchor:
                anchors[variant] = anchor
        return anchors

    @staticmethod
    def _load_segment_boundaries(workspace: Path) -> list[float]:
        """Load segment boundary times from encoding-plan.json.

        Returns a list of boundary timestamps (end times of segments),
        useful for placing transition-variant B-roll at moment junctions.
        """
        plan_path = workspace / "encoding-plan.json"
        try:
            raw = plan_path.read_text()
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []

        boundaries: list[float] = []
        commands = data.get("commands", [])
        for cmd in commands:
            end = cmd.get("end_s")
            if end is not None:
                boundaries.append(float(end))
        return sorted(boundaries)

    @staticmethod
    def _resolve_transition_point(
        boundaries: list[float],
        total_duration_s: float,
        clip_duration: float,
    ) -> float:
        """Pick the best segment boundary for a transition-variant clip.

        Picks the boundary closest to the middle of the reel to maximize
        visual impact. Falls back to the reel midpoint if no boundaries exist.
        """
        if not boundaries:
            return max(0.0, total_duration_s / 2.0 - clip_duration / 2.0)

        mid = total_duration_s / 2.0
        best = min(boundaries, key=lambda b: abs(b - mid))
        return max(0.0, best - clip_duration / 2.0)

    @staticmethod
    def _match_anchor(anchor: str, segments: list[dict[str, object]]) -> tuple[int, float]:
        """Match a narrative anchor to the best segment via Jaccard keyword similarity.

        Args:
            anchor: Narrative anchor text to match.
            segments: Segment dicts with optional ``transcript_text`` key.

        Returns:
            ``(segment_index, confidence_score)`` — the best-matching segment.
        """
        anchor_words = set(anchor.lower().split())
        if not anchor_words:
            return (0, 0.0)

        best_idx = 0
        best_score = 0.0

        for i, seg in enumerate(segments):
            text = str(seg.get("transcript_text", ""))
            seg_words = set(text.lower().split())
            if not seg_words:
                continue
            intersection = anchor_words & seg_words
            union = anchor_words | seg_words
            jaccard = len(intersection) / len(union) if union else 0.0
            if jaccard > best_score:
                best_score = jaccard
                best_idx = i

        return (best_idx, best_score)

    @staticmethod
    def _estimate_clip_duration(clip: dict[str, object]) -> float:
        """Estimate clip duration from job metadata, defaulting to 6s."""
        raw = clip.get("duration_s")
        if raw is not None:
            try:
                val = float(str(raw))
                if val > 0:
                    return val
            except (ValueError, TypeError):
                pass
        return 6.0
