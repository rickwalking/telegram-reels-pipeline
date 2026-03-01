"""ManifestBuildHook — build unified cutaway manifest before Assembly stage."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Literal

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import StageHook

logger = logging.getLogger(__name__)


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

        try:
            from pipeline.application.broll_placer import BrollPlacer
            from pipeline.application.manifest_builder import ManifestBuilder

            builder = ManifestBuilder(BrollPlacer())
            manifest, dropped = await builder.build(workspace, segments, total_duration)
            path = await builder.write_manifest(manifest, dropped, workspace)
            print(
                f"  [MANIFEST] Built cutaway manifest: "
                f"{len(manifest.clips)} clips, {len(dropped)} dropped -> {path.name}"
            )
        except Exception:
            logger.warning("Cutaway manifest build failed — continuing without manifest", exc_info=True)
            print("  [MANIFEST] Build failed — continuing without cutaway manifest")
