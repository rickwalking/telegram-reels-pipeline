"""ManifestBuildHook — build unified cutaway manifest before Assembly stage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import StageHook

logger = logging.getLogger(__name__)

# Heuristic placement hints → relative position in timeline (0.0-1.0)
_PLACEMENT_HINTS: dict[str, float] = {
    "intro": 0.05,
    "beginning": 0.05,
    "start": 0.05,
    "middle": 0.50,
    "mid": 0.50,
    "center": 0.50,
    "outro": 0.90,
    "end": 0.90,
    "conclusion": 0.90,
}
_DEFAULT_CLIP_DURATION: float = 5.0


class ManifestBuildHook:
    """Build unified cutaway manifest before Assembly stage.

    Reads ``encoding-plan.json`` from the workspace, extracts segment
    data (start, end, transcript text), calculates total duration, and
    uses ``ManifestBuilder`` with ``BrollPlacer`` to produce
    ``cutaway-manifest.json``.

    Non-fatal: the pipeline continues without a manifest on failure.
    """

    if TYPE_CHECKING:
        _protocol_check: StageHook

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool:
        """Return True only for Assembly + pre."""
        return stage == PipelineStage.ASSEMBLY and phase == "pre"

    async def execute(self, context: PipelineContext) -> None:
        """Read encoding plan, build cutaway manifest, and write atomically."""
        workspace = context.require_workspace()
        plan_path = workspace / "encoding-plan.json"
        if not plan_path.exists():
            return

        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Cannot read encoding-plan.json for cutaway manifest: %s", exc)
            return

        segments, total_duration = _extract_segments(plan)
        await self._build_manifest(workspace, segments, total_duration)

    @staticmethod
    async def _build_manifest(
        workspace: Path,
        segments: list[dict[str, object]],
        total_duration: float,
    ) -> None:
        """Build and write the manifest, merging user-instructed clips."""
        try:
            from pipeline.application.broll_placer import BrollPlacer
            from pipeline.application.manifest_builder import ManifestBuilder
            from pipeline.domain.models import CutawayManifest, resolve_overlaps

            builder = ManifestBuilder(BrollPlacer())
            manifest, dropped = await builder.build(workspace, segments, total_duration)

            user_clips = _read_user_instructed_clips(workspace, total_duration)
            if user_clips:
                all_clips = manifest.clips + user_clips
                kept, extra_dropped = resolve_overlaps(all_clips)
                kept_sorted = tuple(sorted(kept, key=lambda c: c.insertion_point_s))
                manifest = CutawayManifest(clips=kept_sorted)
                dropped = dropped + extra_dropped

            path = await builder.write_manifest(manifest, dropped, workspace)
            print(
                f"  [MANIFEST] Built cutaway manifest: "
                f"{len(manifest.clips)} clips, {len(dropped)} dropped -> {path.name}"
            )
        except Exception:
            logger.warning("Cutaway manifest build failed — continuing without manifest", exc_info=True)
            print("  [MANIFEST] Build failed — continuing without cutaway manifest")


def _extract_segments(plan: dict[str, Any]) -> tuple[list[dict[str, object]], float]:
    """Extract segment data and total duration from an encoding plan."""
    commands = plan.get("commands", [])
    segments: list[dict[str, object]] = []
    for cmd in commands:
        seg: dict[str, object] = {}
        if "start_s" in cmd:
            seg["start_s"] = cmd["start_s"]
        if "end_s" in cmd:
            seg["end_s"] = cmd["end_s"]
        if "transcript_text" in cmd:
            seg["transcript_text"] = cmd["transcript_text"]
        if seg:
            segments.append(seg)

    total_duration = float(plan.get("total_duration_seconds", 0.0))
    if total_duration <= 0 and commands:
        last_end = commands[-1].get("end_s", 0.0)
        total_duration = float(last_end) if last_end else 0.0

    return segments, total_duration


def _read_user_instructed_clips(workspace: Path, total_duration_s: float) -> tuple[Any, ...]:
    """Read documentary_clips from router-output.json and convert to CutawayClip objects.

    Returns a tuple of ``CutawayClip`` instances for clips with valid local
    file paths.  Clips referencing non-existent files are logged and skipped.
    """
    from pipeline.domain.models import ClipSource, CutawayClip

    router_path = workspace / "router-output.json"
    try:
        data = json.loads(router_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ()

    raw_clips = data.get("documentary_clips", [])
    if not isinstance(raw_clips, list):
        return ()

    clips: list[CutawayClip] = []
    for i, entry in enumerate(raw_clips):
        if not isinstance(entry, dict):
            continue
        path_or_query = str(entry.get("path_or_query", ""))
        if not path_or_query:
            continue

        # Resolve relative paths against workspace
        clip_path = Path(path_or_query)
        if not clip_path.is_absolute():
            clip_path = workspace / clip_path

        if not clip_path.exists():
            logger.warning("documentary_clips[%d]: file not found — %s", i, clip_path)
            continue

        placement_hint = str(entry.get("placement_hint", "")).strip().lower()
        relative_pos = _PLACEMENT_HINTS.get(placement_hint, 0.5)
        insertion_s = max(0.0, total_duration_s * relative_pos)

        clips.append(
            CutawayClip(
                source=ClipSource.USER_PROVIDED,
                variant="broll",
                clip_path=str(clip_path),
                insertion_point_s=insertion_s,
                duration_s=_DEFAULT_CLIP_DURATION,
                narrative_anchor=placement_hint or "user-instructed",
                match_confidence=1.0,
            )
        )

    return tuple(clips)
