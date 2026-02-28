"""ManifestBuilder — build unified CutawayManifest from Veo3 + external clip sources."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path

from pipeline.application.broll_placer import BrollPlacer
from pipeline.domain.models import (
    ClipSource,
    CutawayClip,
    CutawayManifest,
)

logger = logging.getLogger(__name__)

# Minimum Jaccard similarity for anchor matching (same as BrollPlacer)
_MIN_MATCH_CONFIDENCE: float = 0.3


class ManifestBuilder:
    """Build a unified CutawayManifest from Veo3 and external clip sources.

    Reads completed Veo3 clips via ``BrollPlacer``, reads user-provided or
    resolver-produced ``external-clips.json``, merges them into a single
    ``CutawayManifest`` with overlap resolution, and writes the result to
    ``cutaway-manifest.json``.
    """

    def __init__(self, broll_placer: BrollPlacer) -> None:
        self._broll_placer = broll_placer

    async def build(
        self,
        workspace: Path,
        segments: list[dict[str, object]],
        total_duration_s: float,
    ) -> tuple[CutawayManifest, tuple[CutawayClip, ...]]:
        """Build a unified manifest from all clip sources.

        Args:
            workspace: Pipeline run workspace directory.
            segments: List of segment dicts with ``start_s``, ``end_s``,
                and optionally ``transcript_text``.
            total_duration_s: Total reel duration in seconds.

        Returns:
            ``(manifest, dropped)`` — the unified manifest and any clips
            dropped due to overlap resolution.
        """
        # Resolve Veo3 placements via BrollPlacer
        broll = await asyncio.to_thread(
            self._broll_placer.resolve_placements,
            workspace,
            segments,
            total_duration_s,
        )

        # Read external clips
        external = await asyncio.to_thread(
            self._read_external_clips,
            workspace,
            segments,
            total_duration_s,
        )

        # Merge via domain factory (handles overlap resolution + sorting)
        manifest, dropped = CutawayManifest.from_broll_and_external(broll, external)
        return manifest, dropped

    async def write_manifest(
        self,
        manifest: CutawayManifest,
        dropped: tuple[CutawayClip, ...],
        workspace: Path,
    ) -> Path:
        """Write the manifest to ``cutaway-manifest.json`` atomically.

        Args:
            manifest: The unified manifest to serialize.
            dropped: Clips dropped due to overlap resolution.
            workspace: Pipeline run workspace directory.

        Returns:
            Path to the written manifest file.
        """
        return await asyncio.to_thread(self._write_manifest_sync, manifest, dropped, workspace)

    @staticmethod
    def _write_manifest_sync(
        manifest: CutawayManifest,
        dropped: tuple[CutawayClip, ...],
        workspace: Path,
    ) -> Path:
        """Synchronous atomic write of cutaway-manifest.json."""
        manifest_path = workspace / "cutaway-manifest.json"

        data = {
            "clips": [
                {
                    "source": clip.source.value,
                    "variant": clip.variant,
                    "clip_path": clip.clip_path,
                    "insertion_point_s": clip.insertion_point_s,
                    "duration_s": clip.duration_s,
                    "narrative_anchor": clip.narrative_anchor,
                    "match_confidence": clip.match_confidence,
                }
                for clip in manifest.clips
            ],
            "dropped": [
                {
                    "source": clip.source.value,
                    "variant": clip.variant,
                    "clip_path": clip.clip_path,
                    "insertion_point_s": clip.insertion_point_s,
                    "duration_s": clip.duration_s,
                    "narrative_anchor": clip.narrative_anchor,
                    "match_confidence": clip.match_confidence,
                }
                for clip in dropped
            ],
            "total_clips": len(manifest.clips),
            "total_dropped": len(dropped),
        }

        fd, tmp_path = tempfile.mkstemp(dir=str(workspace), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(manifest_path))
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

        return manifest_path

    @staticmethod
    def _read_external_clips(
        workspace: Path,
        segments: list[dict[str, object]],
        total_duration_s: float,
    ) -> tuple[CutawayClip, ...]:
        """Read external-clips.json and convert entries to CutawayClip.

        Handles two formats:

        - **CLI format**: top-level JSON array with ``insertion_point_s``,
          ``clip_path``, ``duration_s`` -> ``ClipSource.USER_PROVIDED``
        - **Resolver format**: ``{"clips": [...]}`` with ``local_path``,
          ``duration`` -> ``ClipSource.EXTERNAL`` (needs anchor matching
          for insertion_point_s)
        """
        clips_path = workspace / "external-clips.json"
        try:
            raw = clips_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return ()

        if isinstance(data, list):
            # CLI format: top-level array
            return ManifestBuilder._parse_cli_format(data, workspace)
        if isinstance(data, dict):
            # Resolver format: {"clips": [...]}
            entries = data.get("clips", [])
            if not isinstance(entries, list):
                return ()
            # Read suggestion anchors for matching
            anchors = ManifestBuilder._read_suggestions_anchors(workspace)
            return ManifestBuilder._parse_resolver_format(entries, segments, total_duration_s, anchors)
        return ()

    @staticmethod
    def _parse_cli_format(
        entries: list[object],
        workspace: Path,
    ) -> tuple[CutawayClip, ...]:
        """Parse CLI-format external clips (top-level array).

        Each entry has ``insertion_point_s``, ``clip_path``, ``duration_s``.
        Source is ``ClipSource.USER_PROVIDED``.
        """
        clips: list[CutawayClip] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            clip_path = str(entry.get("clip_path", ""))
            if not clip_path:
                continue
            # Resolve relative paths against workspace
            if not Path(clip_path).is_absolute():
                clip_path = str(workspace / clip_path)
            try:
                insertion = float(str(entry.get("insertion_point_s", 0.0)))
                duration = float(str(entry.get("duration_s", 6.0)))
            except (ValueError, TypeError):
                continue
            if duration <= 0:
                continue

            clips.append(
                CutawayClip(
                    source=ClipSource.USER_PROVIDED,
                    variant="broll",
                    clip_path=clip_path,
                    insertion_point_s=max(0.0, insertion),
                    duration_s=duration,
                    narrative_anchor="",
                    match_confidence=1.0,
                )
            )
        return tuple(clips)

    @staticmethod
    def _parse_resolver_format(
        entries: list[object],
        segments: list[dict[str, object]],
        total_duration_s: float,
        anchors: dict[str, str],
    ) -> tuple[CutawayClip, ...]:
        """Parse resolver-format external clips (``{"clips": [...]}``.

        Each entry has ``local_path``, ``duration``, optionally ``label``.
        Source is ``ClipSource.EXTERNAL``.  Insertion point is derived via
        anchor matching against segments.
        """
        clips: list[CutawayClip] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            local_path = str(entry.get("local_path", ""))
            if not local_path:
                continue
            try:
                duration = float(str(entry.get("duration", 6.0) or 6.0))
            except (ValueError, TypeError):
                duration = 6.0
            if duration <= 0:
                continue

            label = str(entry.get("label", ""))
            search_query = str(entry.get("search_query", ""))

            # Try to find anchor text for this clip
            anchor = anchors.get(search_query, "") or anchors.get(label, "") or label or search_query

            # Derive insertion point from anchor matching
            insertion, confidence = ManifestBuilder._match_anchor(anchor, segments)
            if confidence < _MIN_MATCH_CONFIDENCE and segments:
                # Weak match — place at reel midpoint as fallback
                insertion = max(0.0, total_duration_s / 2.0 - duration / 2.0)
                confidence = 0.1

            clips.append(
                CutawayClip(
                    source=ClipSource.EXTERNAL,
                    variant="broll",
                    clip_path=local_path,
                    insertion_point_s=max(0.0, insertion),
                    duration_s=duration,
                    narrative_anchor=anchor,
                    match_confidence=confidence,
                )
            )
        return tuple(clips)

    @staticmethod
    def _match_anchor(
        anchor: str,
        segments: list[dict[str, object]],
    ) -> tuple[float, float]:
        """Match an anchor to a segment and return (insertion_point_s, confidence).

        Reuses BrollPlacer's Jaccard approach for keyword matching, then
        derives the insertion point from the matched segment's midpoint.
        """
        if not segments or not anchor:
            return (0.0, 0.0)

        seg_idx, confidence = BrollPlacer._match_anchor(anchor, segments)
        seg = segments[seg_idx]
        seg_start = float(str(seg.get("start_s", 0.0) or 0.0))
        seg_end = float(str(seg.get("end_s", seg_start) or seg_start))
        midpoint = seg_start + (seg_end - seg_start) / 2.0
        return (midpoint, confidence)

    @staticmethod
    def _read_suggestions_anchors(workspace: Path) -> dict[str, str]:
        """Read narrative_anchor values from publishing-assets.json suggestions.

        Returns a dict mapping ``search_query`` to ``narrative_anchor`` for
        each external clip suggestion.
        """
        assets_path = workspace / "publishing-assets.json"
        try:
            raw = assets_path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

        result: dict[str, str] = {}
        suggestions = data.get("external_clip_suggestions", [])
        if not isinstance(suggestions, list):
            return {}
        for suggestion in suggestions:
            if not isinstance(suggestion, dict):
                continue
            query = str(suggestion.get("search_query", ""))
            anchor = str(suggestion.get("narrative_anchor", ""))
            if query and anchor:
                result[query] = anchor
        return result
