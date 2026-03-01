"""Tests for DownloadCutawaysCommand — parsing, download orchestration, manifest, atomic writes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.application.cli.commands.download_cutaways import (
    DownloadCutawaysCommand,
    _download_cutaway_clips,
    parse_cutaway_spec,
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


class StubClipDownloader:
    """Stub ExternalClipDownloaderPort that returns pre-configured paths."""

    def __init__(self, results: list[Path | None]) -> None:
        self._results = results
        self._call_idx = 0
        self.download_calls: list[tuple[str, Path]] = []

    async def download(self, url: str, dest_dir: Path) -> Path | None:
        self.download_calls.append((url, dest_dir))
        idx = self._call_idx
        self._call_idx += 1
        return self._results[idx] if idx < len(self._results) else None


class StubDurationProber:
    """Stub ClipDurationProber that returns pre-configured durations."""

    def __init__(self, results: list[float | None]) -> None:
        self._results = results
        self._call_idx = 0
        self.probe_calls: list[Path] = []

    async def probe(self, clip_path: Path) -> float | None:
        self.probe_calls.append(clip_path)
        idx = self._call_idx
        self._call_idx += 1
        return self._results[idx] if idx < len(self._results) else None


# ---------------------------------------------------------------------------
# parse_cutaway_spec
# ---------------------------------------------------------------------------


class TestParseCutawaySpec:
    """URL@TIMESTAMP parsing -- split on last @ character."""

    def test_simple_url_and_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/video.mp4@30")
        assert url == "https://example.com/video.mp4"
        assert ts == 30.0

    def test_float_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/video.mp4@45.5")
        assert url == "https://example.com/video.mp4"
        assert ts == 45.5

    def test_zero_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/video.mp4@0")
        assert url == "https://example.com/video.mp4"
        assert ts == 0.0

    def test_url_with_at_sign_in_path(self) -> None:
        """URLs like https://example.com/@user/video should split on last @."""
        url, ts = parse_cutaway_spec("https://example.com/@user/video@30")
        assert url == "https://example.com/@user/video"
        assert ts == 30.0

    def test_url_with_multiple_at_signs(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/@channel/@user/clip@120")
        assert url == "https://example.com/@channel/@user/clip"
        assert ts == 120.0

    def test_missing_at_sign_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            parse_cutaway_spec("https://example.com/video.mp4")

    def test_at_sign_at_start_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            parse_cutaway_spec("@30")

    def test_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="expected a number"):
            parse_cutaway_spec("https://example.com/video.mp4@notanumber")

    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >= 0"):
            parse_cutaway_spec("https://example.com/video.mp4@-5")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            parse_cutaway_spec("")

    def test_large_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/video@9999.99")
        assert url == "https://example.com/video"
        assert ts == 9999.99


# ---------------------------------------------------------------------------
# _download_cutaway_clips
# ---------------------------------------------------------------------------


class TestDownloadCutawayClips:
    """Download orchestration, manifest format, partial failure handling."""

    def test_successful_download_writes_manifest(self, tmp_path: Path) -> None:
        """Single clip downloads successfully and manifest is written."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip_file = clips_dir / "clip-abc.mp4"
        clip_file.write_bytes(b"fake video data")

        downloader = StubClipDownloader([clip_file])
        prober = StubDurationProber([12.5])

        manifest = asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/video.mp4@30"],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert len(manifest) == 1
        assert manifest[0]["url"] == "https://example.com/video.mp4"
        assert manifest[0]["insertion_point_s"] == 30.0
        assert manifest[0]["duration_s"] == 12.5
        assert manifest[0]["clip_path"] == "external_clips/cutaway-0.mp4"

        manifest_file = tmp_path / "external-clips.json"
        assert manifest_file.exists()
        saved = json.loads(manifest_file.read_text())
        assert len(saved) == 1
        assert saved[0]["url"] == "https://example.com/video.mp4"

    def test_multiple_clips(self, tmp_path: Path) -> None:
        """Multiple clips all download successfully."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip1 = clips_dir / "clip-abc.mp4"
        clip2 = clips_dir / "clip-def.mp4"
        clip1.write_bytes(b"fake1")
        clip2.write_bytes(b"fake2")

        downloader = StubClipDownloader([clip1, clip2])
        prober = StubDurationProber([10.0, 15.0])

        manifest = asyncio.run(
            _download_cutaway_clips(
                [
                    "https://example.com/a.mp4@10",
                    "https://example.com/b.mp4@60",
                ],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert len(manifest) == 2
        assert manifest[0]["insertion_point_s"] == 10.0
        assert manifest[1]["insertion_point_s"] == 60.0

    def test_partial_failure_skips_failed(self, tmp_path: Path) -> None:
        """One download fails, others succeed -- partial success."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip2 = clips_dir / "clip-def.mp4"
        clip2.write_bytes(b"fake2")

        downloader = StubClipDownloader([None, clip2])
        prober = StubDurationProber([8.0])

        manifest = asyncio.run(
            _download_cutaway_clips(
                [
                    "https://example.com/fail.mp4@10",
                    "https://example.com/ok.mp4@60",
                ],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert len(manifest) == 1
        assert manifest[0]["url"] == "https://example.com/ok.mp4"
        assert manifest[0]["clip_path"] == "external_clips/cutaway-1.mp4"

    def test_invalid_spec_skipped(self, tmp_path: Path) -> None:
        """Invalid cutaway spec is skipped gracefully."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip-abc.mp4"
        clip.write_bytes(b"fake")

        downloader = StubClipDownloader([clip])
        prober = StubDurationProber([5.0])

        manifest = asyncio.run(
            _download_cutaway_clips(
                [
                    "no-at-sign-here",
                    "https://example.com/ok.mp4@30",
                ],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert len(manifest) == 1
        assert manifest[0]["url"] == "https://example.com/ok.mp4"

    def test_all_downloads_fail_writes_empty_manifest(self, tmp_path: Path) -> None:
        """All downloads fail -- manifest is written but empty."""
        downloader = StubClipDownloader([None])
        prober = StubDurationProber([])

        manifest = asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/fail.mp4@10"],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert manifest == []
        manifest_file = tmp_path / "external-clips.json"
        assert manifest_file.exists()
        assert json.loads(manifest_file.read_text()) == []

    def test_duration_probe_failure_skips_clip(self, tmp_path: Path) -> None:
        """Clip downloads OK but duration probe fails -- clip skipped."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip-abc.mp4"
        clip.write_bytes(b"fake")

        downloader = StubClipDownloader([clip])
        prober = StubDurationProber([None])

        manifest = asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/video.mp4@30"],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert manifest == []

    def test_manifest_json_format(self, tmp_path: Path) -> None:
        """Verify the exact JSON structure of external-clips.json."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip-abc.mp4"
        clip.write_bytes(b"fake")

        downloader = StubClipDownloader([clip])
        prober = StubDurationProber([7.25])

        asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/@user/vid@45.5"],
                tmp_path,
                downloader,
                prober,
            )
        )

        saved = json.loads((tmp_path / "external-clips.json").read_text())
        assert len(saved) == 1
        entry = saved[0]
        assert entry == {
            "url": "https://example.com/@user/vid",
            "clip_path": "external_clips/cutaway-0.mp4",
            "insertion_point_s": 45.5,
            "duration_s": 7.25,
        }

    def test_creates_external_clips_directory(self, tmp_path: Path) -> None:
        """external_clips/ directory is created if it doesn't exist."""
        downloader = StubClipDownloader([None])
        prober = StubDurationProber([])

        asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/fail.mp4@10"],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert (tmp_path / "external_clips").is_dir()

    def test_empty_specs_list_writes_empty_manifest(self, tmp_path: Path) -> None:
        """Empty specs list produces an empty manifest."""
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])

        manifest = asyncio.run(_download_cutaway_clips([], tmp_path, downloader, prober))
        assert manifest == []
        assert json.loads((tmp_path / "external-clips.json").read_text()) == []

    def test_downloader_receives_correct_url(self, tmp_path: Path) -> None:
        """Verify the downloader receives the parsed URL, not the full spec."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip.mp4"
        clip.write_bytes(b"fake")

        downloader = StubClipDownloader([clip])
        prober = StubDurationProber([5.0])

        asyncio.run(
            _download_cutaway_clips(
                ["https://example.com/video@30"],
                tmp_path,
                downloader,
                prober,
            )
        )

        assert len(downloader.download_calls) == 1
        assert downloader.download_calls[0][0] == "https://example.com/video"


# ---------------------------------------------------------------------------
# Atomic write tests
# ---------------------------------------------------------------------------


class TestDownloadCutawayClipsAtomicWrite:
    """Verify atomic write in _download_cutaway_clips cleans up on failure."""

    async def test_os_replace_failure_cleans_temp(self, tmp_path: Path) -> None:
        """When os.replace raises, temp file is cleaned up and exception re-raised."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        clips_dir = workspace / "external_clips"
        clips_dir.mkdir(parents=True)
        clip_file = clips_dir / "raw.mp4"
        clip_file.write_bytes(b"video")

        downloader = StubClipDownloader([clip_file])
        prober = StubDurationProber([5.0])

        with (
            patch(
                "pipeline.application.cli.commands.download_cutaways.parse_cutaway_spec",
                return_value=("https://example.com/vid", 10.0),
            ),
            patch(
                "pipeline.application.cli.commands.download_cutaways.os.replace",
                side_effect=OSError("disk full"),
            ),
            pytest.raises(OSError, match="disk full"),
        ):
            await _download_cutaway_clips(
                ["https://example.com/vid@10.0"],
                workspace,
                downloader,
                prober,
            )

        # No temp files left behind
        tmp_files = list(workspace.glob("*.tmp"))
        assert tmp_files == []

    async def test_successful_write_no_temp_files(self, tmp_path: Path) -> None:
        """Normal case: external-clips.json written atomically, no temp leftovers."""
        workspace = tmp_path / "ws"
        workspace.mkdir()

        clips_dir = workspace / "external_clips"
        clips_dir.mkdir(parents=True)
        clip_file = clips_dir / "raw.mp4"
        clip_file.write_bytes(b"video")

        downloader = StubClipDownloader([clip_file])
        prober = StubDurationProber([5.0])

        with patch(
            "pipeline.application.cli.commands.download_cutaways.parse_cutaway_spec",
            return_value=("https://example.com/vid", 10.0),
        ):
            manifest = await _download_cutaway_clips(
                ["https://example.com/vid@10.0"],
                workspace,
                downloader,
                prober,
            )

        assert len(manifest) == 1
        manifest_path = workspace / "external-clips.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert len(data) == 1

        # No temp files left behind
        tmp_files = list(workspace.glob("*.tmp"))
        assert tmp_files == []


# ---------------------------------------------------------------------------
# DownloadCutawaysCommand — integration
# ---------------------------------------------------------------------------


class TestDownloadCutawaysCommand:
    """Command-level tests with stub protocols."""

    def test_no_cutaway_specs_returns_early(self, tmp_path: Path) -> None:
        ctx = _make_context(workspace=tmp_path)
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert "No cutaway" in result.message

    def test_none_cutaway_specs_returns_early(self, tmp_path: Path) -> None:
        ctx = _make_context(workspace=tmp_path)
        ctx.state["cutaway_specs"] = None
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert "No cutaway" in result.message

    def test_empty_list_cutaway_specs_returns_early(self, tmp_path: Path) -> None:
        ctx = _make_context(workspace=tmp_path)
        ctx.state["cutaway_specs"] = []
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert "No cutaway" in result.message

    def test_downloads_and_reports_success(self, tmp_path: Path) -> None:
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip.mp4"
        clip.write_bytes(b"fake")

        ctx = _make_context(workspace=tmp_path)
        ctx.state["cutaway_specs"] = ["https://example.com/video@30"]

        downloader = StubClipDownloader([clip])
        prober = StubDurationProber([10.0])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        result = asyncio.run(cmd.execute(ctx))
        assert result.success is True
        assert result.data.get("manifest_count") == 1
        assert result.data.get("specs_count") == 1

    def test_requires_workspace(self) -> None:
        ctx = _make_context()
        ctx.state["cutaway_specs"] = ["https://example.com/video@30"]
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        with pytest.raises(RuntimeError, match="workspace has not been set"):
            asyncio.run(cmd.execute(ctx))

    def test_name_property(self) -> None:
        downloader = StubClipDownloader([])
        prober = StubDurationProber([])
        cmd = DownloadCutawaysCommand(clip_downloader=downloader, duration_prober=prober)
        assert cmd.name == "download-cutaways"


# ---------------------------------------------------------------------------
# Cutaway argparse patterns (parsing tests)
# ---------------------------------------------------------------------------


class TestCutawayArgparse:
    """Verify cutaway spec patterns used by argparse --cutaway."""

    def test_single_cutaway_spec(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/v@30")
        assert url == "https://example.com/v"
        assert ts == 30.0

    def test_multiple_cutaway_specs(self) -> None:
        specs = [
            "https://example.com/a@10",
            "https://example.com/b@60",
        ]
        results = [parse_cutaway_spec(s) for s in specs]
        assert results[0] == ("https://example.com/a", 10.0)
        assert results[1] == ("https://example.com/b", 60.0)

    def test_cutaway_with_at_in_url(self) -> None:
        url, ts = parse_cutaway_spec("https://youtube.com/@channel/video@30")
        assert url == "https://youtube.com/@channel/video"
        assert ts == 30.0

    def test_cutaway_zero_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/v@0")
        assert url == "https://example.com/v"
        assert ts == 0.0

    def test_cutaway_float_timestamp(self) -> None:
        url, ts = parse_cutaway_spec("https://example.com/v@45.5")
        assert url == "https://example.com/v"
        assert ts == 45.5
