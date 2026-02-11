"""Frontmatter serialization — RunState ↔ YAML frontmatter in run.md files."""

from __future__ import annotations

import yaml

from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId


def serialize_run_state(state: RunState) -> str:
    """Convert a RunState to a YAML frontmatter string with --- delimiters."""
    data = {
        "run_id": str(state.run_id),
        "youtube_url": state.youtube_url,
        "current_stage": state.current_stage.value,
        "current_attempt": state.current_attempt,
        "qa_status": state.qa_status.value,
        "stages_completed": list(state.stages_completed),
        "escalation_state": state.escalation_state.value,
        "best_of_three_overrides": list(state.best_of_three_overrides),
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "workspace_path": state.workspace_path,
    }
    body = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
    return f"---\n{body}---\n"


def deserialize_run_state(content: str) -> RunState:
    """Parse YAML frontmatter from run.md content and reconstruct a RunState.

    Raises ValueError if frontmatter is missing or malformed.
    """
    if not content.startswith("---"):
        raise ValueError("Missing YAML frontmatter delimiters (---)")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Missing YAML frontmatter delimiters (---)")

    raw = yaml.safe_load(parts[1])
    if not isinstance(raw, dict):
        raise ValueError("Frontmatter is not a valid YAML mapping")

    try:
        return RunState(
            run_id=RunId(str(raw["run_id"])),
            youtube_url=str(raw["youtube_url"]),
            current_stage=PipelineStage(raw["current_stage"]),
            current_attempt=int(raw["current_attempt"]),
            qa_status=QAStatus(raw["qa_status"]),
            stages_completed=tuple(str(s) for s in raw.get("stages_completed", [])),
            escalation_state=EscalationState(raw["escalation_state"]),
            best_of_three_overrides=tuple(str(s) for s in raw.get("best_of_three_overrides", [])),
            created_at=str(raw.get("created_at", "")),
            updated_at=str(raw.get("updated_at", "")),
            workspace_path=str(raw.get("workspace_path", "")),
        )
    except KeyError as e:
        raise ValueError(f"Missing required key in frontmatter: {e}") from e
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid value in frontmatter: {e}") from e
