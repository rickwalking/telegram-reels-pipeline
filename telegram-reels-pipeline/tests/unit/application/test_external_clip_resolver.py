"""Tests for ExternalClipResolver — search, download, rate limiting, error handling."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pipeline.application.external_clip_resolver import (
    _INTER_SEARCH_DELAY,
    _MAX_DURATION,
    _MAX_SEARCHES,
    ExternalClipResolver,
)

# ---------------------------------------------------------------------------
# Fake downloader
# ---------------------------------------------------------------------------


class FakeDownloader:
    """Fake ExternalClipDownloaderPort for testing."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.download_calls: list[tuple[str, Path]] = []

    async def download(self, url: str, dest_dir: Path) -> Path | None:
        self.download_calls.append((url, dest_dir))
        if self._fail:
            return None
        clip_dir = dest_dir / "external_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)
        fake_path = clip_dir / "clip-fake.mp4"
        fake_path.write_bytes(b"fake-video")
        return fake_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_suggestion(
    query: str = "documentary b-roll ocean",
    label: str = "ocean",
    timing_hint: str = "intro",
) -> dict[str, object]:
    return {"search_query": query, "label": label, "timing_hint": timing_hint}


def _make_search_output(
    url: str = "https://www.youtube.com/watch?v=abc123",
    duration: int = 30,
    width: int = 1080,
    height: int = 1920,
) -> bytes:
    """Build yt-dlp --flat-playlist --dump-json output."""
    data = {"url": url, "duration": duration, "width": width, "height": height}
    return json.dumps(data).encode()


def _make_proc_mock(
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> AsyncMock:
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ---------------------------------------------------------------------------
# TestSearchYouTube
# ---------------------------------------------------------------------------


class TestSearchYouTube:
    async def test_successful_search_returns_metadata(self) -> None:
        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("ocean documentary short")

        assert result is not None
        assert result["url"] == "https://www.youtube.com/watch?v=abc123"
        assert result["duration"] == 30
        assert result["width"] == 1080
        assert result["height"] == 1920

    async def test_search_filters_long_clips(self) -> None:
        output = _make_search_output(duration=120)
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("long video")

        assert result is None

    async def test_search_accepts_clips_at_max_duration(self) -> None:
        output = _make_search_output(duration=_MAX_DURATION)
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("exact limit")

        assert result is not None

    async def test_search_returns_none_on_nonzero_exit(self) -> None:
        proc = _make_proc_mock(returncode=1, stderr=b"error")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("bad query")

        assert result is None

    async def test_search_returns_none_on_empty_stdout(self) -> None:
        proc = _make_proc_mock(stdout=b"")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("no output")

        assert result is None

    async def test_search_returns_none_on_invalid_json(self) -> None:
        proc = _make_proc_mock(stdout=b"not json")
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("bad json")

        assert result is None

    async def test_search_returns_none_on_oserror(self) -> None:
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("not found")):
            result = await ExternalClipResolver._search_youtube("missing yt-dlp")

        assert result is None

    async def test_search_builds_url_from_id(self) -> None:
        data = {"id": "xyz789", "duration": 15}
        proc = _make_proc_mock(stdout=json.dumps(data).encode())
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("id-only result")

        assert result is not None
        assert result["url"] == "https://www.youtube.com/watch?v=xyz789"

    async def test_search_returns_none_on_no_url_or_id(self) -> None:
        data = {"duration": 15, "title": "no url"}
        proc = _make_proc_mock(stdout=json.dumps(data).encode())
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("no url result")

        assert result is None

    async def test_search_prefers_url_over_id(self) -> None:
        data = {"url": "https://youtube.com/shorts/abc", "id": "xyz", "duration": 10}
        proc = _make_proc_mock(stdout=json.dumps(data).encode())
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await ExternalClipResolver._search_youtube("url preferred")

        assert result is not None
        assert result["url"] == "https://youtube.com/shorts/abc"


# ---------------------------------------------------------------------------
# TestResolveAll
# ---------------------------------------------------------------------------


class TestResolveAll:
    async def test_resolves_single_suggestion(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await resolver.resolve_all([_make_suggestion()], tmp_path)

        assert len(result) == 1
        assert result[0]["search_query"] == "documentary b-roll ocean"
        assert result[0]["url"] == "https://www.youtube.com/watch?v=abc123"
        assert result[0]["label"] == "ocean"
        assert result[0]["timing_hint"] == "intro"
        assert len(downloader.download_calls) == 1

    async def test_caps_at_max_searches(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        suggestions = [_make_suggestion(query=f"query-{i}") for i in range(_MAX_SEARCHES + 5)]

        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            await resolver.resolve_all(suggestions, tmp_path)

        # Only MAX_SEARCHES should be processed
        assert len(downloader.download_calls) == _MAX_SEARCHES

    async def test_rate_limiting_delay_between_searches(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        suggestions = [_make_suggestion(query=f"q-{i}") for i in range(3)]

        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("pipeline.application.external_clip_resolver.asyncio.sleep", side_effect=fake_sleep),
        ):
            await resolver.resolve_all(suggestions, tmp_path)

        # Should sleep between searches: 2 delays for 3 searches
        assert len(sleep_calls) == 2
        assert all(d == _INTER_SEARCH_DELAY for d in sleep_calls)

    async def test_no_delay_before_first_search(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        suggestions = [_make_suggestion()]

        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with (
            patch("asyncio.create_subprocess_exec", return_value=proc),
            patch("pipeline.application.external_clip_resolver.asyncio.sleep", side_effect=fake_sleep),
        ):
            await resolver.resolve_all(suggestions, tmp_path)

        assert len(sleep_calls) == 0

    async def test_skips_empty_search_query(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        suggestions = [{"search_query": "", "label": "empty"}]

        result = await resolver.resolve_all(suggestions, tmp_path)

        assert len(result) == 0
        assert len(downloader.download_calls) == 0

    async def test_skips_failed_search(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        proc = _make_proc_mock(returncode=1)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await resolver.resolve_all([_make_suggestion()], tmp_path)

        assert len(result) == 0
        assert len(downloader.download_calls) == 0

    async def test_skips_failed_download(self, tmp_path: Path) -> None:
        downloader = FakeDownloader(fail=True)
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        output = _make_search_output()
        proc = _make_proc_mock(stdout=output)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await resolver.resolve_all([_make_suggestion()], tmp_path)

        assert len(result) == 0
        assert len(downloader.download_calls) == 1

    async def test_returns_empty_on_empty_suggestions(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        result = await resolver.resolve_all([], tmp_path)

        assert result == []

    async def test_continues_after_individual_exception(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        call_count = 0

        async def flaky_search(query: str) -> dict[str, object] | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient error")
            return {
                "url": "https://www.youtube.com/watch?v=ok",
                "duration": 20,
                "width": 1080,
                "height": 1920,
            }

        suggestions = [_make_suggestion(query="fail"), _make_suggestion(query="succeed")]

        with patch.object(ExternalClipResolver, "_search_youtube", side_effect=flaky_search):
            result = await resolver.resolve_all(suggestions, tmp_path)

        # First fails, second succeeds
        assert len(result) == 1
        assert result[0]["search_query"] == "succeed"


# ---------------------------------------------------------------------------
# TestWriteManifest
# ---------------------------------------------------------------------------


class TestWriteManifest:
    async def test_writes_json_to_workspace(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        resolved = [
            {
                "search_query": "ocean documentary",
                "url": "https://youtube.com/shorts/abc",
                "local_path": "/tmp/clip.mp4",
                "duration": 25,
            }
        ]

        manifest_path = await resolver.write_manifest(resolved, tmp_path)

        assert manifest_path == tmp_path / "external-clips.json"
        assert manifest_path.exists()

        data = json.loads(manifest_path.read_text())
        assert "clips" in data
        assert len(data["clips"]) == 1
        assert data["clips"][0]["url"] == "https://youtube.com/shorts/abc"

    async def test_writes_empty_manifest(self, tmp_path: Path) -> None:
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        manifest_path = await resolver.write_manifest([], tmp_path)

        data = json.loads(manifest_path.read_text())
        assert data["clips"] == []

    async def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Verify atomic write pattern works (write-to-tmp + rename)."""
        downloader = FakeDownloader()
        resolver = ExternalClipResolver(downloader)  # type: ignore[arg-type]

        resolved = [{"search_query": "test", "url": "https://example.com", "local_path": "/t.mp4", "duration": 5}]
        manifest_path = await resolver.write_manifest(resolved, tmp_path)

        # File should exist and be valid JSON
        content = json.loads(manifest_path.read_text())
        assert content["clips"][0]["search_query"] == "test"


# ---------------------------------------------------------------------------
# TestConstants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_searches_is_3(self) -> None:
        assert _MAX_SEARCHES == 3

    def test_inter_search_delay_is_2(self) -> None:
        assert _INTER_SEARCH_DELAY == 2.0

    def test_max_duration_is_60(self) -> None:
        assert _MAX_DURATION == 60
