"""RevisionHandler — execute targeted revisions without re-running the full pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from pipeline.domain.enums import PipelineStage, RevisionType
from pipeline.domain.errors import PipelineError
from pipeline.domain.models import RevisionRequest, RevisionResult

logger = logging.getLogger(__name__)

# Which stages each revision type needs to re-run
_REVISION_STAGES: dict[RevisionType, tuple[PipelineStage, ...]] = {
    RevisionType.EXTEND_MOMENT: (
        PipelineStage.FFMPEG_ENGINEER,
        PipelineStage.ASSEMBLY,
        PipelineStage.DELIVERY,
    ),
    RevisionType.FIX_FRAMING: (
        PipelineStage.FFMPEG_ENGINEER,
        PipelineStage.ASSEMBLY,
        PipelineStage.DELIVERY,
    ),
    RevisionType.DIFFERENT_MOMENT: (
        PipelineStage.TRANSCRIPT,
        PipelineStage.CONTENT,
        PipelineStage.LAYOUT_DETECTIVE,
        PipelineStage.FFMPEG_ENGINEER,
        PipelineStage.ASSEMBLY,
        PipelineStage.DELIVERY,
    ),
    RevisionType.ADD_CONTEXT: (
        PipelineStage.FFMPEG_ENGINEER,
        PipelineStage.ASSEMBLY,
        PipelineStage.DELIVERY,
    ),
}


class RevisionError(PipelineError):
    """Failed to execute a revision."""


class RevisionHandler:
    """Execute targeted revision workflows without full pipeline re-runs.

    Each revision type only re-processes the stages that need updating,
    preserving unchanged artifacts.
    """

    async def handle(self, request: RevisionRequest, workspace: Path) -> RevisionResult:
        """Dispatch a revision request to the appropriate handler.

        Returns a RevisionResult with the re-processed artifacts and
        which stages were re-run.
        """
        handler_map = {
            RevisionType.EXTEND_MOMENT: self._extend_moment,
            RevisionType.FIX_FRAMING: self._fix_framing,
            RevisionType.DIFFERENT_MOMENT: self._different_moment,
            RevisionType.ADD_CONTEXT: self._add_context,
        }

        handler = handler_map[request.revision_type]
        logger.info("Handling %s revision for run %s", request.revision_type.value, request.run_id)

        artifacts = await handler(request, workspace)
        stages = _REVISION_STAGES[request.revision_type]

        return RevisionResult(
            revision_type=request.revision_type,
            original_run_id=request.run_id,
            artifacts=artifacts,
            stages_rerun=tuple(s.value for s in stages),
        )

    async def _extend_moment(self, request: RevisionRequest, workspace: Path) -> tuple[Path, ...]:
        """Extend the selected moment by adjusting timestamps."""
        moment_file = workspace / "assets" / "moment-selection.json"
        exists = await asyncio.to_thread(moment_file.exists)
        if not exists:
            logger.warning("No moment-selection.json found — cannot extend moment")
            return ()

        try:
            raw = await asyncio.to_thread(moment_file.read_text)
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RevisionError(f"Failed to read moment selection: {exc}") from exc

        extra = request.extra_seconds or 15.0
        data["start_seconds"] = max(0.0, data.get("start_seconds", 0.0) - extra)
        data["end_seconds"] = data.get("end_seconds", 60.0) + extra

        revised_file = workspace / "assets" / "moment-selection-revised.json"
        await asyncio.to_thread(revised_file.write_text, json.dumps(data, indent=2))
        logger.info("Extended moment: start=%.1f, end=%.1f", data["start_seconds"], data["end_seconds"])

        return (revised_file,)

    async def _fix_framing(self, request: RevisionRequest, workspace: Path) -> tuple[Path, ...]:
        """Fix framing on a specific segment by adjusting crop region."""
        layout_file = workspace / "assets" / "layout-segments.json"
        exists = await asyncio.to_thread(layout_file.exists)
        if not exists:
            logger.warning("No layout-segments.json found — cannot fix framing")
            return ()

        try:
            raw = await asyncio.to_thread(layout_file.read_text)
            segments = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RevisionError(f"Failed to read layout segments: {exc}") from exc

        target = request.target_segment or 0
        if target < len(segments):
            segments[target]["needs_reframe"] = True
            segments[target]["user_instruction"] = request.user_message
            logger.info("Marked segment %d for reframing", target)

        revised_file = workspace / "assets" / "layout-segments-revised.json"
        await asyncio.to_thread(revised_file.write_text, json.dumps(segments, indent=2))

        return (revised_file,)

    async def _different_moment(self, request: RevisionRequest, workspace: Path) -> tuple[Path, ...]:
        """Request a different moment — triggers full downstream re-processing."""
        hint: dict[str, object] = {
            "type": "different_moment",
            "user_message": request.user_message,
        }
        if request.timestamp_hint is not None:
            hint["timestamp_hint"] = request.timestamp_hint

        hint_file = workspace / "assets" / "revision-hint.json"
        await asyncio.to_thread(hint_file.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(hint_file.write_text, json.dumps(hint, indent=2))
        logger.info("Created different-moment hint at timestamp=%.1f", request.timestamp_hint or 0.0)

        return (hint_file,)

    async def _add_context(self, request: RevisionRequest, workspace: Path) -> tuple[Path, ...]:
        """Add surrounding context to the clip by widening the timestamp window."""
        moment_file = workspace / "assets" / "moment-selection.json"
        exists = await asyncio.to_thread(moment_file.exists)
        if not exists:
            logger.warning("No moment-selection.json found — cannot add context")
            return ()

        try:
            raw = await asyncio.to_thread(moment_file.read_text)
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RevisionError(f"Failed to read moment selection: {exc}") from exc

        extra = request.extra_seconds or 30.0
        data["start_seconds"] = max(0.0, data.get("start_seconds", 0.0) - extra)
        data["end_seconds"] = data.get("end_seconds", 60.0) + extra
        data["context_added"] = True
        data["user_instruction"] = request.user_message

        revised_file = workspace / "assets" / "moment-selection-revised.json"
        await asyncio.to_thread(revised_file.write_text, json.dumps(data, indent=2))
        logger.info("Added context: start=%.1f, end=%.1f", data["start_seconds"], data["end_seconds"])

        return (revised_file,)

    @staticmethod
    def stages_for(revision_type: RevisionType) -> tuple[PipelineStage, ...]:
        """Return which pipeline stages a given revision type needs to re-run."""
        return _REVISION_STAGES[revision_type]
