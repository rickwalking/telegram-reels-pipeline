"""ResumePointDetectorService — pure function to detect the next stage to resume from."""

from __future__ import annotations

from pipeline.domain.event_types import PipelineStateEvent

_DEFAULT_RESUME_STAGE = "router"
_STAGE_COMPLETED_EVENT = "stage_completed"


def detect_resume_point(events: tuple[PipelineStateEvent, ...]) -> str:
    """Determine which stage to resume from based on the event log.

    Scans events in reverse order to find the last ``stage_completed`` event
    and returns the next stage name. Falls back to ``"router"`` when no
    completed stage events are found.

    Args:
        events: Ordered tuple of pipeline state events, earliest first.

    Returns:
        Stage name string to resume from.
    """
    last_completed_stage = _find_last_completed_stage(events)
    if last_completed_stage is None:
        return _DEFAULT_RESUME_STAGE
    return _next_stage_after(last_completed_stage)


def _find_last_completed_stage(events: tuple[PipelineStateEvent, ...]) -> str | None:
    """Return the stage_name from the last stage_completed event, or None."""
    for event in reversed(events):
        if event.event_name == _STAGE_COMPLETED_EVENT and event.stage_name:
            return event.stage_name
    return None


def _next_stage_after(completed_stage_name: str) -> str:
    """Return the stage that follows the given completed stage in sequence."""
    from pipeline.domain.transitions import STAGE_ORDER

    stage_values = [stage.value for stage in STAGE_ORDER]
    if completed_stage_name not in stage_values:
        return _DEFAULT_RESUME_STAGE

    completed_index = stage_values.index(completed_stage_name)
    next_index = completed_index + 1

    if next_index >= len(stage_values):
        return completed_stage_name

    return stage_values[next_index]
