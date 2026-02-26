"""Tests for ExternalClipDownloader — ExternalClipDownloaderPort via yt-dlp + ffmpeg."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pipeline.domain.ports import ExternalClipDownloaderPort
from pipeline.infrastructure.adapters.external_clip_downloader import ExternalClipDownloader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    return proc


def _ffprobe_resolution_json(width: int = 1080, height: int = 1920) -> str:
    return json.dumps({"streams": [{"width": width, "height": height}]})


def _ffprobe_audio_json(has_audio: bool = True) -> str:
    if has_audio:
        return json.dumps({"streams": [{"codec_type": "audio"}]})
    return json.dumps({"streams": []})


def _ffprobe_duration_json(duration: float = 5.0) -> str:
    return json.dumps({"streams": [{"duration": duration}]})


# ---------------------------------------------------------------------------
# FakeExternalClipDownloader
# ---------------------------------------------------------------------------

class FakeExternalClipDownloader:
    """Test double for ExternalClipDownloaderPort."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.downloaded_urls: list[str] = []

    async def download(self, url: str, dest_dir: Path) -> Path | None:
        self.downloaded_urls.append(url)
        if self._fail:
            return None
        clip_dir = dest_dir / "external_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        out = clip_dir / f"fake-{hash(url) & 0xFFFF:04x}.mp4"
        out.write_bytes(b"")
        return out


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocol:
    def test_satisfies_external_clip_downloader_port(self) -> None:
        adapter = ExternalClipDownloader()
        assert isinstance(adapter, ExternalClipDownloaderPort)

    def test_fake_satisfies_external_clip_downloader_port(self) -> None:
        fake = FakeExternalClipDownloader()
        assert isinstance(fake, ExternalClipDownloaderPort)


# ---------------------------------------------------------------------------
# FakeExternalClipDownloader tests
# ---------------------------------------------------------------------------

class TestFakeExternalClipDownloader:
    async def test_success_creates_file(self, tmp_path: Path) -> None:
        fake = FakeExternalClipDownloader()
        result = await fake.download("https://example.com/clip.mp4", tmp_path)

        assert result is not None
        assert result.exists()
        assert result.parent.name == "external_clips"
        assert fake.downloaded_urls == ["https://example.com/clip.mp4"]

    async def test_failure_returns_none(self, tmp_path: Path) -> None:
        fake = FakeExternalClipDownloader(fail=True)
        result = await fake.download("https://example.com/clip.mp4", tmp_path)

        assert result is None
        assert fake.downloaded_urls == ["https://example.com/clip.mp4"]

    async def test_tracks_multiple_downloads(self, tmp_path: Path) -> None:
        fake = FakeExternalClipDownloader()
        await fake.download("https://example.com/a.mp4", tmp_path)
        await fake.download("https://example.com/b.mp4", tmp_path)

        assert len(fake.downloaded_urls) == 2


# ---------------------------------------------------------------------------
# Download command construction
# ---------------------------------------------------------------------------

class TestDownloadCommand:
    async def test_ytdlp_args_contain_url(self, tmp_path: Path) -> None:
        """Verify yt-dlp is called with correct arguments including the URL."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"

        ytdlp_proc = _make_proc(returncode=0)

        calls: list[tuple[str, ...]] = []

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            calls.append(args)
            if args[0] == "yt-dlp":
                # Simulate file creation
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return ytdlp_proc
            if args[0] == "ffprobe":
                # Audio probe
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=False))
                # Resolution probe
                if "stream=width,height" in args:
                    return _make_proc(stdout=_ffprobe_resolution_json(1080, 1920))
                # Duration probe
                if "stream=duration" in args:
                    return _make_proc(stdout=_ffprobe_duration_json(5.0))
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        # Check yt-dlp was called with the URL
        ytdlp_calls = [c for c in calls if c[0] == "yt-dlp"]
        assert len(ytdlp_calls) == 1
        assert url in ytdlp_calls[0]
        assert "-f" in ytdlp_calls[0]
        assert "bestvideo[ext=mp4]/best[ext=mp4]/best" in ytdlp_calls[0]
        assert result is not None


# ---------------------------------------------------------------------------
# Audio stripping
# ---------------------------------------------------------------------------

class TestAudioStripping:
    async def test_strips_audio_when_present(self, tmp_path: Path) -> None:
        """When ffprobe detects audio, ffmpeg -an should be called."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"
        calls: list[tuple[str, ...]] = []

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            calls.append(args)
            if args[0] == "yt-dlp":
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return _make_proc()
            if args[0] == "ffprobe":
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=True))
                if "stream=width,height" in args:
                    return _make_proc(stdout=_ffprobe_resolution_json(1080, 1920))
                if "stream=duration" in args:
                    return _make_proc(stdout=_ffprobe_duration_json(5.0))
            if args[0] == "ffmpeg":
                # Simulate ffmpeg creating the output file
                output_path = args[-1]
                Path(output_path).write_bytes(b"stripped-video")
                return _make_proc()
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            await adapter.download(url, tmp_path)

        ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
        strip_calls = [c for c in ffmpeg_calls if "-an" in c]
        assert len(strip_calls) == 1
        assert "-c:v" in strip_calls[0]
        assert "copy" in strip_calls[0]


# ---------------------------------------------------------------------------
# Upscale logic
# ---------------------------------------------------------------------------

class TestUpscaleLogic:
    async def test_upscale_triggered_when_not_target_resolution(self, tmp_path: Path) -> None:
        """When ffprobe reports non-1080x1920, upscale ffmpeg should be called."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"
        calls: list[tuple[str, ...]] = []

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            calls.append(args)
            if args[0] == "yt-dlp":
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return _make_proc()
            if args[0] == "ffprobe":
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=False))
                if "stream=width,height" in args:
                    return _make_proc(stdout=_ffprobe_resolution_json(720, 1280))
                if "stream=duration" in args:
                    return _make_proc(stdout=_ffprobe_duration_json(5.0))
            if args[0] == "ffmpeg":
                output_path = args[-1]
                Path(output_path).write_bytes(b"upscaled-video")
                return _make_proc()
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
        upscale_calls = [c for c in ffmpeg_calls if any("scale=" in str(a) for a in c)]
        assert len(upscale_calls) == 1
        assert "scale=1080:1920:flags=lanczos" in upscale_calls[0]
        assert result is not None

    async def test_no_upscale_when_already_target_resolution(self, tmp_path: Path) -> None:
        """When ffprobe reports 1080x1920, no upscale ffmpeg call should happen."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"
        calls: list[tuple[str, ...]] = []

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            calls.append(args)
            if args[0] == "yt-dlp":
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return _make_proc()
            if args[0] == "ffprobe":
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=False))
                if "stream=width,height" in args:
                    return _make_proc(stdout=_ffprobe_resolution_json(1080, 1920))
                if "stream=duration" in args:
                    return _make_proc(stdout=_ffprobe_duration_json(5.0))
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        ffmpeg_calls = [c for c in calls if c[0] == "ffmpeg"]
        upscale_calls = [c for c in ffmpeg_calls if any("scale=" in str(a) for a in c)]
        assert len(upscale_calls) == 0
        assert result is not None


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

class TestFailureHandling:
    async def test_ytdlp_failure_returns_none(self, tmp_path: Path) -> None:
        """When yt-dlp exits non-zero, download returns None."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            if args[0] == "yt-dlp":
                return _make_proc(returncode=1, stderr="ERROR: Unsupported URL")
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        assert result is None

    async def test_partial_file_cleanup_on_failure(self, tmp_path: Path) -> None:
        """When download fails after yt-dlp succeeds, intermediate files are cleaned up."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"
        call_count = 0

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if args[0] == "yt-dlp":
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return _make_proc()
            if args[0] == "ffprobe":
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=False))
                if "stream=width,height" in args:
                    # Return empty streams to cause probe failure -> None
                    return _make_proc(stdout=json.dumps({"streams": []}))
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        assert result is None
        # Intermediate raw file should be cleaned up
        clip_dir = tmp_path / "external_clips"
        raw_files = list(clip_dir.glob("*-raw.mp4"))
        assert len(raw_files) == 0

    async def test_oserror_on_ytdlp_returns_none(self, tmp_path: Path) -> None:
        """When yt-dlp is not found (OSError), download returns None."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"

        async def raise_oserror(*args: str, **kwargs: object) -> None:
            raise OSError("yt-dlp not found")

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=raise_oserror,
        ):
            result = await adapter.download(url, tmp_path)

        assert result is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    async def test_validation_fails_when_duration_zero(self, tmp_path: Path) -> None:
        """When ffprobe reports duration 0, download returns None."""
        adapter = ExternalClipDownloader()
        url = "https://example.com/video.mp4"

        async def capture_exec(*args: str, **kwargs: object) -> MagicMock:
            if args[0] == "yt-dlp":
                for i, arg in enumerate(args):
                    if arg == "-o" and i + 1 < len(args):
                        Path(args[i + 1]).write_bytes(b"fake-video")
                return _make_proc()
            if args[0] == "ffprobe":
                if "-select_streams" in args and "a:0" in args:
                    return _make_proc(stdout=_ffprobe_audio_json(has_audio=False))
                if "stream=width,height" in args:
                    return _make_proc(stdout=_ffprobe_resolution_json(1080, 1920))
                if "stream=duration" in args:
                    return _make_proc(stdout=_ffprobe_duration_json(0.0))
            return _make_proc()

        with patch(
            "pipeline.infrastructure.adapters.external_clip_downloader.asyncio.create_subprocess_exec",
            side_effect=capture_exec,
        ):
            result = await adapter.download(url, tmp_path)

        assert result is None
