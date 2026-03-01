"""Stage registry — single source of truth for pipeline stage definitions."""

from __future__ import annotations

from pipeline.domain.enums import PipelineStage

# All pipeline stages in order (delivery skipped — no Telegram).
# Each tuple: (PipelineStage, step_file, agent_definition, gate_name)
ALL_STAGES: tuple[tuple[PipelineStage, str, str, str], ...] = (
    (PipelineStage.ROUTER, "stage-01-router.md", "router", "router"),
    (PipelineStage.RESEARCH, "stage-02-research.md", "research", "research"),
    (PipelineStage.TRANSCRIPT, "stage-03-transcript.md", "transcript", "transcript"),
    (PipelineStage.CONTENT, "stage-04-content.md", "content-creator", "content"),
    (PipelineStage.LAYOUT_DETECTIVE, "stage-05-layout-detective.md", "layout-detective", "layout"),
    (PipelineStage.FFMPEG_ENGINEER, "stage-06-ffmpeg-engineer.md", "ffmpeg-engineer", "ffmpeg"),
    (PipelineStage.ASSEMBLY, "stage-07-assembly.md", "qa", "assembly"),
)

TOTAL_CLI_STAGES: int = len(ALL_STAGES)

# Signature artifacts per stage (1-indexed). A stage is "complete" if at least
# one of its signature artifacts exists in the workspace.
STAGE_SIGNATURES: dict[int, tuple[str, ...]] = {
    1: ("router-output.json",),
    2: ("research-output.json",),
    3: ("moment-selection.json",),
    4: ("content.json",),
    5: ("layout-analysis.json",),
    6: ("encoding-plan.json", "segment-001.mp4"),
    7: ("final-reel.mp4",),
}


def stage_name(stage_num: int) -> str:
    """Return the human-readable display name for a 1-indexed stage number."""
    if 1 <= stage_num <= TOTAL_CLI_STAGES:
        return ALL_STAGES[stage_num - 1][0].value.replace("_", "-")
    return f"stage-{stage_num}"
