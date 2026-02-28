"""Tests for --cutaway CLI flag: parsing, download orchestration, manifest."""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add scripts parent so we can import run_cli — must precede the import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import run_cli

# ---------------------------------------------------------------------------
# _parse_cutaway_spec
# ---------------------------------------------------------------------------


class TestParseCutawaySpec:
    """URL@TIMESTAMP parsing — split on last @ character."""

    def test_simple_url_and_timestamp(self) -> None:
        url, ts = run_cli._parse_cutaway_spec("https://example.com/video.mp4@30")
        assert url == "https://example.com/video.mp4"
        assert ts == 30.0

    def test_float_timestamp(self) -> None:
        url, ts = run_cli._parse_cutaway_spec("https://example.com/video.mp4@45.5")
        assert url == "https://example.com/video.mp4"
        assert ts == 45.5

    def test_zero_timestamp(self) -> None:
        url, ts = run_cli._parse_cutaway_spec("https://example.com/video.mp4@0")
        assert url == "https://example.com/video.mp4"
        assert ts == 0.0

    def test_url_with_at_sign_in_path(self) -> None:
        """URLs like https://example.com/@user/video should split on last @."""
        url, ts = run_cli._parse_cutaway_spec("https://example.com/@user/video@30")
        assert url == "https://example.com/@user/video"
        assert ts == 30.0

    def test_url_with_multiple_at_signs(self) -> None:
        url, ts = run_cli._parse_cutaway_spec("https://example.com/@channel/@user/clip@120")
        assert url == "https://example.com/@channel/@user/clip"
        assert ts == 120.0

    def test_missing_at_sign_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            run_cli._parse_cutaway_spec("https://example.com/video.mp4")

    def test_at_sign_at_start_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            run_cli._parse_cutaway_spec("@30")

    def test_invalid_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="expected a number"):
            run_cli._parse_cutaway_spec("https://example.com/video.mp4@notanumber")

    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="must be >= 0"):
            run_cli._parse_cutaway_spec("https://example.com/video.mp4@-5")

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid cutaway spec"):
            run_cli._parse_cutaway_spec("")

    def test_large_timestamp(self) -> None:
        url, ts = run_cli._parse_cutaway_spec("https://example.com/video@9999.99")
        assert url == "https://example.com/video"
        assert ts == 9999.99


# ---------------------------------------------------------------------------
# _probe_clip_duration
# ---------------------------------------------------------------------------


class TestProbeClipDuration:
    """ffprobe duration detection for downloaded clips."""

    def test_returns_duration_on_success(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"12.500000\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.run(run_cli._probe_clip_duration(Path("/fake/clip.mp4")))

        assert result == 12.5

    def test_returns_none_on_nonzero_exit(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.run(run_cli._probe_clip_duration(Path("/fake/clip.mp4")))

        assert result is None

    def test_returns_none_on_invalid_output(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"N/A\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = asyncio.run(run_cli._probe_clip_duration(Path("/fake/clip.mp4")))

        assert result is None

    def test_returns_none_on_os_error(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("ffprobe not found")):
            result = asyncio.run(run_cli._probe_clip_duration(Path("/fake/clip.mp4")))

        assert result is None

    def test_passes_correct_ffprobe_args(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"5.0\n", b""))
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            asyncio.run(run_cli._probe_clip_duration(Path("/fake/clip.mp4")))

        args = mock_exec.call_args[0]
        assert args[0] == "ffprobe"
        assert "-show_entries" in args
        assert "format=duration" in args


# ---------------------------------------------------------------------------
# _download_cutaway_clips
# ---------------------------------------------------------------------------


class TestDownloadCutawayClips:
    """Download orchestration, manifest format, partial failure handling."""

    def _make_downloader_mock(
        self,
        results: list[Path | None],
    ) -> MagicMock:
        """Create a mock ExternalClipDownloader that returns paths in sequence."""
        call_idx = [0]

        async def _download(url: str, dest_dir: Path) -> Path | None:
            idx = call_idx[0]
            call_idx[0] += 1
            return results[idx] if idx < len(results) else None

        mock = MagicMock()
        mock.download = AsyncMock(side_effect=_download)
        return mock

    def test_successful_download_writes_manifest(self, tmp_path: Path) -> None:
        """Single clip downloads successfully and manifest is written."""
        # Pre-create the clip file that the downloader would produce
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip_file = clips_dir / "clip-abc.mp4"
        clip_file.write_bytes(b"fake video data")

        downloader = self._make_downloader_mock([clip_file])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(return_value=12.5)),
        ):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    ["https://example.com/video.mp4@30"],
                    tmp_path,
                )
            )

        assert len(manifest) == 1
        assert manifest[0]["url"] == "https://example.com/video.mp4"
        assert manifest[0]["insertion_point_s"] == 30.0
        assert manifest[0]["duration_s"] == 12.5
        assert manifest[0]["clip_path"] == "external_clips/cutaway-0.mp4"

        # Verify manifest file written
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

        downloader = self._make_downloader_mock([clip1, clip2])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(side_effect=[10.0, 15.0])),
        ):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    [
                        "https://example.com/a.mp4@10",
                        "https://example.com/b.mp4@60",
                    ],
                    tmp_path,
                )
            )

        assert len(manifest) == 2
        assert manifest[0]["insertion_point_s"] == 10.0
        assert manifest[1]["insertion_point_s"] == 60.0

    def test_partial_failure_skips_failed(self, tmp_path: Path) -> None:
        """One download fails, others succeed — partial success."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip2 = clips_dir / "clip-def.mp4"
        clip2.write_bytes(b"fake2")

        # First download fails (None), second succeeds
        downloader = self._make_downloader_mock([None, clip2])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(return_value=8.0)),
        ):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    [
                        "https://example.com/fail.mp4@10",
                        "https://example.com/ok.mp4@60",
                    ],
                    tmp_path,
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

        downloader = self._make_downloader_mock([clip])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(return_value=5.0)),
        ):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    [
                        "no-at-sign-here",  # invalid — no @
                        "https://example.com/ok.mp4@30",
                    ],
                    tmp_path,
                )
            )

        assert len(manifest) == 1
        assert manifest[0]["url"] == "https://example.com/ok.mp4"

    def test_all_downloads_fail_writes_empty_manifest(self, tmp_path: Path) -> None:
        """All downloads fail — manifest is written but empty."""
        downloader = self._make_downloader_mock([None])

        with patch.object(run_cli, "ExternalClipDownloader", return_value=downloader):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    ["https://example.com/fail.mp4@10"],
                    tmp_path,
                )
            )

        assert manifest == []
        manifest_file = tmp_path / "external-clips.json"
        assert manifest_file.exists()
        assert json.loads(manifest_file.read_text()) == []

    def test_duration_probe_failure_skips_clip(self, tmp_path: Path) -> None:
        """Clip downloads OK but duration probe fails — clip skipped."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip-abc.mp4"
        clip.write_bytes(b"fake")

        downloader = self._make_downloader_mock([clip])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(return_value=None)),
        ):
            manifest = asyncio.run(
                run_cli._download_cutaway_clips(
                    ["https://example.com/video.mp4@30"],
                    tmp_path,
                )
            )

        assert manifest == []

    def test_manifest_json_format(self, tmp_path: Path) -> None:
        """Verify the exact JSON structure of external-clips.json."""
        clips_dir = tmp_path / "external_clips"
        clips_dir.mkdir(parents=True)
        clip = clips_dir / "clip-abc.mp4"
        clip.write_bytes(b"fake")

        downloader = self._make_downloader_mock([clip])

        with (
            patch.object(run_cli, "ExternalClipDownloader", return_value=downloader),
            patch.object(run_cli, "_probe_clip_duration", new=AsyncMock(return_value=7.25)),
        ):
            asyncio.run(
                run_cli._download_cutaway_clips(
                    ["https://example.com/@user/vid@45.5"],
                    tmp_path,
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
        downloader = self._make_downloader_mock([None])

        with patch.object(run_cli, "ExternalClipDownloader", return_value=downloader):
            asyncio.run(
                run_cli._download_cutaway_clips(
                    ["https://example.com/fail.mp4@10"],
                    tmp_path,
                )
            )

        assert (tmp_path / "external_clips").is_dir()

    def test_empty_specs_list_writes_empty_manifest(self, tmp_path: Path) -> None:
        """Empty specs list produces an empty manifest."""
        manifest = asyncio.run(run_cli._download_cutaway_clips([], tmp_path))
        assert manifest == []
        assert json.loads((tmp_path / "external-clips.json").read_text()) == []


# ---------------------------------------------------------------------------
# --cutaway argparse argument
# ---------------------------------------------------------------------------


class TestCutawayArgparse:
    """Verify --cutaway argparse behavior."""

    def _make_parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser()
        p.add_argument("url", nargs="?", default="http://example.com")
        p.add_argument("--cutaway", action="append", default=None, metavar="URL@TIMESTAMP")
        return p

    def test_default_is_none(self) -> None:
        p = self._make_parser()
        args = p.parse_args([])
        assert args.cutaway is None

    def test_single_cutaway(self) -> None:
        p = self._make_parser()
        args = p.parse_args(["--cutaway", "https://example.com/v@30"])
        assert args.cutaway == ["https://example.com/v@30"]

    def test_multiple_cutaways(self) -> None:
        p = self._make_parser()
        args = p.parse_args(
            [
                "--cutaway",
                "https://example.com/a@10",
                "--cutaway",
                "https://example.com/b@60",
            ]
        )
        assert args.cutaway == [
            "https://example.com/a@10",
            "https://example.com/b@60",
        ]

    def test_cutaway_with_other_args(self) -> None:
        p = self._make_parser()
        args = p.parse_args(
            [
                "https://youtube.com/watch?v=123",
                "--cutaway",
                "https://example.com/v@30",
            ]
        )
        assert args.url == "https://youtube.com/watch?v=123"
        assert args.cutaway == ["https://example.com/v@30"]
