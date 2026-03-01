"""Tests for ValidateArgsCommand — argument validation, resume detection, moments computation."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

from pipeline.application.cli.commands.validate_args import (
    TOTAL_CLI_STAGES,
    ValidateArgsCommand,
    compute_moments_requested,
    detect_resume_stage,
)
from pipeline.application.cli.context import PipelineContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    return PipelineContext(**defaults)  # type: ignore[arg-type]


def _make_args(**overrides: object) -> argparse.Namespace:
    """Build an argparse.Namespace with sensible defaults."""
    defaults: dict[str, object] = {
        "url": "http://example.com",
        "stages": 7,
        "resume": None,
        "start_stage": None,
        "target_duration": 90,
        "moments": None,
        "style": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# compute_moments_requested
# ---------------------------------------------------------------------------


class TestComputeMomentsRequested:
    """Auto-trigger formula and explicit override."""

    def test_short_duration_returns_one(self) -> None:
        assert compute_moments_requested(90, None) == 1

    def test_boundary_120_returns_one(self) -> None:
        assert compute_moments_requested(120, None) == 1

    def test_just_above_threshold_returns_two(self) -> None:
        assert compute_moments_requested(121, None) == 2

    def test_180s_returns_three(self) -> None:
        assert compute_moments_requested(180, None) == 3

    def test_240s_returns_four(self) -> None:
        assert compute_moments_requested(240, None) == 4

    def test_300s_returns_five(self) -> None:
        assert compute_moments_requested(300, None) == 5

    def test_max_capped_at_five(self) -> None:
        assert compute_moments_requested(600, None) == 5

    def test_30s_returns_one(self) -> None:
        assert compute_moments_requested(30, None) == 1

    def test_150s_rounds_up_to_three(self) -> None:
        # 150/60 = 2.5 -- rounds up to 3 (not banker's rounding)
        assert compute_moments_requested(150, None) == 3

    def test_149s_rounds_down_to_two(self) -> None:
        # 149/60 ~ 2.483 -- rounds down to 2
        assert compute_moments_requested(149, None) == 2

    def test_explicit_one_overrides_long_duration(self) -> None:
        assert compute_moments_requested(300, 1) == 1

    def test_explicit_three_overrides_short_duration(self) -> None:
        assert compute_moments_requested(90, 3) == 3

    def test_explicit_five(self) -> None:
        assert compute_moments_requested(120, 5) == 5

    def test_explicit_two(self) -> None:
        assert compute_moments_requested(200, 2) == 2


# ---------------------------------------------------------------------------
# detect_resume_stage
# ---------------------------------------------------------------------------


class TestDetectResumeStage:
    def test_empty_workspace_returns_none(self, tmp_path: Path) -> None:
        assert detect_resume_stage(tmp_path) is None

    def test_detects_stage_2_after_router(self, tmp_path: Path) -> None:
        (tmp_path / "router-output.json").write_text("{}")
        assert detect_resume_stage(tmp_path) == 2

    def test_detects_stage_4_after_transcript(self, tmp_path: Path) -> None:
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "research-output.json").write_text("{}")
        (tmp_path / "moment-selection.json").write_text("{}")
        assert detect_resume_stage(tmp_path) == 4

    def test_detects_stage_6_after_layout(self, tmp_path: Path) -> None:
        for name in (
            "router-output.json",
            "research-output.json",
            "moment-selection.json",
            "content.json",
            "layout-analysis.json",
        ):
            (tmp_path / name).write_text("{}")
        assert detect_resume_stage(tmp_path) == 6

    def test_all_stages_complete_returns_past_last(self, tmp_path: Path) -> None:
        for name in (
            "router-output.json",
            "research-output.json",
            "moment-selection.json",
            "content.json",
            "layout-analysis.json",
            "encoding-plan.json",
            "segment-001.mp4",
            "final-reel.mp4",
        ):
            (tmp_path / name).write_text("{}")
        assert detect_resume_stage(tmp_path) == TOTAL_CLI_STAGES + 1

    def test_gap_in_stages_stops_at_gap(self, tmp_path: Path) -> None:
        """If stage 1 is complete but stage 2 is missing, returns 2."""
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "moment-selection.json").write_text("{}")
        assert detect_resume_stage(tmp_path) == 2

    def test_transcript_clean_alone_does_not_complete_stage_2(self, tmp_path: Path) -> None:
        """transcript_clean.txt alone does not satisfy Stage 2."""
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "transcript_clean.txt").write_text("text")
        assert detect_resume_stage(tmp_path) == 2


# ---------------------------------------------------------------------------
# ValidateArgsCommand — valid defaults
# ---------------------------------------------------------------------------


class TestValidateArgsCommandDefaults:
    def test_valid_defaults_pass(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args()
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["start_stage"] == 1

    def test_no_args_returns_failure(self) -> None:
        ctx = _make_context()
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "No args" in result.message

    def test_name_property(self) -> None:
        cmd = ValidateArgsCommand()
        assert cmd.name == "validate-args"


# ---------------------------------------------------------------------------
# ValidateArgsCommand — resume validation
# ---------------------------------------------------------------------------


class TestValidateArgsCommandResume:
    def test_resume_nonexistent_path_fails(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path / "nonexistent")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "not a valid directory" in result.message

    def test_resume_existing_path_passes(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True

    def test_resume_file_not_dir_fails(self, tmp_path: Path) -> None:
        f = tmp_path / "somefile.txt"
        f.write_text("not a dir")
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=f)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "not a valid directory" in result.message


# ---------------------------------------------------------------------------
# ValidateArgsCommand — start_stage validation
# ---------------------------------------------------------------------------


class TestValidateArgsCommandStartStage:
    def test_start_stage_without_resume_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(start_stage=3)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "requires --resume" in result.message

    def test_start_stage_zero_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(start_stage=0)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--start-stage must be between" in result.message

    def test_start_stage_too_high_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(start_stage=99)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--start-stage must be between" in result.message

    def test_start_stage_negative_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(start_stage=-1)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--start-stage must be between" in result.message

    def test_valid_resume_with_start_stage_passes(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path, start_stage=5)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["start_stage"] == 5

    def test_auto_detect_sets_start_stage(self, tmp_path: Path) -> None:
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "research-output.json").write_text("{}")
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["start_stage"] == 3

    def test_auto_detect_skipped_when_start_stage_explicit(self, tmp_path: Path) -> None:
        (tmp_path / "router-output.json").write_text("{}")
        (tmp_path / "research-output.json").write_text("{}")
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path, start_stage=1)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["start_stage"] == 1

    def test_auto_detect_empty_workspace_stays_at_1(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["start_stage"] == 1

    def test_start_stage_greater_than_stages_fails(self, tmp_path: Path) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(stages=3, start_stage=5, resume=tmp_path)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "cannot be greater than" in result.message


# ---------------------------------------------------------------------------
# ValidateArgsCommand — stages validation
# ---------------------------------------------------------------------------


class TestValidateArgsCommandStages:
    def test_stages_zero_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(stages=0)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--stages must be between" in result.message

    def test_stages_negative_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(stages=-1)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--stages must be between" in result.message

    def test_stages_too_high_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(stages=99)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--stages must be between" in result.message


# ---------------------------------------------------------------------------
# ValidateArgsCommand — target-duration
# ---------------------------------------------------------------------------


class TestValidateArgsCommandDuration:
    def test_target_duration_too_low_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(target_duration=10)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--target-duration must be between" in result.message

    def test_target_duration_too_high_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(target_duration=500)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--target-duration must be between" in result.message

    def test_target_duration_valid_passes(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(target_duration=120)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["target_duration"] == 120


# ---------------------------------------------------------------------------
# ValidateArgsCommand — moments
# ---------------------------------------------------------------------------


class TestValidateArgsCommandMoments:
    def test_moments_too_low_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(moments=0)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--moments must be between" in result.message

    def test_moments_too_high_fails(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(moments=10)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is False
        assert "--moments must be between" in result.message

    def test_moments_computed_and_stored(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(target_duration=180, moments=None)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["moments_requested"] == 3


# ---------------------------------------------------------------------------
# ValidateArgsCommand — all stages complete (exit early)
# ---------------------------------------------------------------------------


class TestValidateArgsCommandAllComplete:
    def test_auto_detect_all_complete_returns_exit_early(self, tmp_path: Path) -> None:
        for name in (
            "router-output.json",
            "research-output.json",
            "moment-selection.json",
            "content.json",
            "layout-analysis.json",
            "encoding-plan.json",
            "segment-001.mp4",
            "final-reel.mp4",
        ):
            (tmp_path / name).write_text("{}")
        ctx = _make_context()
        ctx.state["args"] = _make_args(resume=tmp_path)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert result.data.get("exit_early") is True
        assert "All" in result.message


# ---------------------------------------------------------------------------
# ValidateArgsCommand — style mapping
# ---------------------------------------------------------------------------


class TestValidateArgsCommandStyle:
    def test_style_none_maps_to_none(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style=None)
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] is None

    def test_style_split_maps_to_split_horizontal(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="split")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] == "split_horizontal"

    def test_style_pip_maps_to_pip(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="pip")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] == "pip"

    def test_style_auto_maps_to_auto(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="auto")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] == "auto"

    def test_style_default_maps_to_default(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="default")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] == "default"

    def test_unknown_style_maps_to_none(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="unknown_value")
        cmd = ValidateArgsCommand()
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert ctx.state["framing_style"] is None

    def test_style_stored_in_context(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(style="auto")
        cmd = ValidateArgsCommand()
        asyncio.run(cmd.execute(ctx))
        assert "framing_style" in ctx.state

    def test_stages_stored_in_context(self) -> None:
        ctx = _make_context()
        ctx.state["args"] = _make_args(stages=5)
        cmd = ValidateArgsCommand()
        asyncio.run(cmd.execute(ctx))
        assert ctx.state["stages"] == 5
