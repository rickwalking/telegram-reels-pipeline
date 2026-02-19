"""Tests for RevisionHandler — targeted revision execution."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.application.revision_handler import _REVISION_STAGES, RevisionHandler
from pipeline.domain.enums import PipelineStage, RevisionType
from pipeline.domain.models import RevisionRequest
from pipeline.domain.types import RunId


def _make_request(
    revision_type: RevisionType = RevisionType.EXTEND_MOMENT,
    extra_seconds: float = 15.0,
    target_segment: int | None = None,
    timestamp_hint: float | None = None,
) -> RevisionRequest:
    return RevisionRequest(
        revision_type=revision_type,
        run_id=RunId("run-test"),
        user_message="test revision message",
        target_segment=target_segment,
        timestamp_hint=timestamp_hint,
        extra_seconds=extra_seconds,
    )


def _make_handler() -> RevisionHandler:
    return RevisionHandler()


def _setup_moment_file(workspace: Path, start: float = 10.0, end: float = 70.0) -> Path:
    assets = workspace / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    moment_file = assets / "moment-selection.json"
    moment_file.write_text(
        json.dumps(
            {
                "start_seconds": start,
                "end_seconds": end,
            }
        )
    )
    return moment_file


def _setup_layout_file(workspace: Path, segments: list[dict[str, object]] | None = None) -> Path:
    assets = workspace / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    layout_file = assets / "layout-segments.json"
    default = [
        {"layout": "speaker_focus", "start": 0, "end": 30},
        {"layout": "side_by_side", "start": 30, "end": 60},
    ]
    layout_file.write_text(json.dumps(segments or default))
    return layout_file


class TestExtendMoment:
    async def test_extends_timestamps(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path, start=20.0, end=80.0)
        handler = _make_handler()
        request = _make_request(RevisionType.EXTEND_MOMENT, extra_seconds=10.0)

        result = await handler.handle(request, tmp_path)

        assert len(result.artifacts) == 1
        revised = json.loads(result.artifacts[0].read_text())
        assert revised["start_seconds"] == 10.0  # 20 - 10
        assert revised["end_seconds"] == 90.0  # 80 + 10

    async def test_clamps_start_to_zero(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path, start=5.0, end=60.0)
        handler = _make_handler()
        request = _make_request(RevisionType.EXTEND_MOMENT, extra_seconds=20.0)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised["start_seconds"] == 0.0

    async def test_defaults_to_15_seconds(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path, start=30.0, end=90.0)
        handler = _make_handler()
        request = _make_request(RevisionType.EXTEND_MOMENT, extra_seconds=0.0)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised["start_seconds"] == 15.0  # 30 - 15 (default)

    async def test_missing_moment_file_returns_empty(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.EXTEND_MOMENT)

        result = await handler.handle(request, tmp_path)
        assert result.artifacts == ()

    async def test_result_includes_stages_rerun(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path)
        handler = _make_handler()
        request = _make_request(RevisionType.EXTEND_MOMENT)

        result = await handler.handle(request, tmp_path)
        assert result.revision_type == RevisionType.EXTEND_MOMENT
        assert result.original_run_id == RunId("run-test")
        assert len(result.stages_rerun) > 0


class TestFixFraming:
    async def test_marks_segment_for_reframe(self, tmp_path: Path) -> None:
        _setup_layout_file(tmp_path)
        handler = _make_handler()
        request = _make_request(RevisionType.FIX_FRAMING, target_segment=1)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised[1]["needs_reframe"] is True
        assert revised[1]["user_instruction"] == "test revision message"

    async def test_defaults_to_segment_zero(self, tmp_path: Path) -> None:
        _setup_layout_file(tmp_path)
        handler = _make_handler()
        request = _make_request(RevisionType.FIX_FRAMING)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised[0].get("needs_reframe") is True

    async def test_missing_layout_file_returns_empty(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.FIX_FRAMING)

        result = await handler.handle(request, tmp_path)
        assert result.artifacts == ()


class TestDifferentMoment:
    async def test_creates_hint_file(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.DIFFERENT_MOMENT, timestamp_hint=2700.0)

        result = await handler.handle(request, tmp_path)

        hint = json.loads(result.artifacts[0].read_text())
        assert hint["type"] == "different_moment"
        assert hint["timestamp_hint"] == 2700.0
        assert hint["user_message"] == "test revision message"

    async def test_no_timestamp_hint(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.DIFFERENT_MOMENT)

        result = await handler.handle(request, tmp_path)

        hint = json.loads(result.artifacts[0].read_text())
        assert "timestamp_hint" not in hint

    async def test_creates_assets_directory(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.DIFFERENT_MOMENT)

        result = await handler.handle(request, tmp_path)
        assert result.artifacts[0].exists()

    async def test_stages_include_full_downstream(self) -> None:
        stages = _REVISION_STAGES[RevisionType.DIFFERENT_MOMENT]
        assert PipelineStage.TRANSCRIPT in stages
        assert PipelineStage.LAYOUT_DETECTIVE in stages
        assert PipelineStage.DELIVERY in stages


class TestAddContext:
    async def test_widens_timestamps(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path, start=40.0, end=100.0)
        handler = _make_handler()
        request = _make_request(RevisionType.ADD_CONTEXT, extra_seconds=20.0)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised["start_seconds"] == 20.0  # 40 - 20
        assert revised["end_seconds"] == 120.0  # 100 + 20
        assert revised["context_added"] is True

    async def test_defaults_to_30_seconds(self, tmp_path: Path) -> None:
        _setup_moment_file(tmp_path, start=40.0, end=100.0)
        handler = _make_handler()
        request = _make_request(RevisionType.ADD_CONTEXT, extra_seconds=0.0)

        result = await handler.handle(request, tmp_path)

        revised = json.loads(result.artifacts[0].read_text())
        assert revised["start_seconds"] == 10.0  # 40 - 30 (default)

    async def test_missing_moment_file_returns_empty(self, tmp_path: Path) -> None:
        handler = _make_handler()
        request = _make_request(RevisionType.ADD_CONTEXT)

        result = await handler.handle(request, tmp_path)
        assert result.artifacts == ()


class TestStagesFor:
    def test_extend_moment_stages(self) -> None:
        stages = RevisionHandler.stages_for(RevisionType.EXTEND_MOMENT)
        assert PipelineStage.FFMPEG_ENGINEER in stages
        assert PipelineStage.ASSEMBLY in stages
        assert PipelineStage.DELIVERY in stages
        assert PipelineStage.TRANSCRIPT not in stages

    def test_different_moment_includes_transcript(self) -> None:
        stages = RevisionHandler.stages_for(RevisionType.DIFFERENT_MOMENT)
        assert PipelineStage.TRANSCRIPT in stages
