"""Tests for Veo3 authenticated video download — operation_name field, download_clip, and jobs.json round-trip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline.application.veo3_orchestrator import Veo3Orchestrator
from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt
from pipeline.infrastructure.adapters.gemini_veo3_adapter import (
    FakeVeo3Adapter,
    GeminiVeo3Adapter,
    Veo3GenerationError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOGLE_MODULES = {"google": MagicMock(), "google.genai": MagicMock(), "google.genai.types": MagicMock()}


def _make_prompt(**overrides: Any) -> Veo3Prompt:
    defaults: dict[str, Any] = {
        "variant": "broll",
        "prompt": "Abstract data visualization",
        "idempotent_key": "run1_broll",
    }
    defaults.update(overrides)
    return Veo3Prompt(**defaults)


def _completed_job(**overrides: Any) -> Veo3Job:
    defaults: dict[str, Any] = {
        "idempotent_key": "run1_broll",
        "variant": "broll",
        "prompt": "Test prompt",
        "status": Veo3JobStatus.COMPLETED,
        "operation_name": "operations/test-op-123",
    }
    defaults.update(overrides)
    return Veo3Job(**defaults)


# ---------------------------------------------------------------------------
# Task 1: Veo3Job operation_name field
# ---------------------------------------------------------------------------


class TestVeo3JobOperationName:
    def test_construction_with_operation_name(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.GENERATING,
            operation_name="operations/generate-abc123",
        )
        assert job.operation_name == "operations/generate-abc123"

    def test_default_operation_name_is_empty(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.PENDING,
        )
        assert job.operation_name == ""

    def test_operation_name_immutable(self) -> None:
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.GENERATING,
            operation_name="operations/test-op",
        )
        with pytest.raises(AttributeError):
            job.operation_name = "modified"  # type: ignore[misc]

    def test_backward_compat_without_operation_name(self) -> None:
        """Existing code that doesn't pass operation_name still works."""
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.COMPLETED,
            video_path="veo3/broll.mp4",
        )
        assert job.operation_name == ""
        assert job.video_path == "veo3/broll.mp4"


# ---------------------------------------------------------------------------
# Task 3: submit_job captures operation_name
# ---------------------------------------------------------------------------


class TestSubmitJobOperationName:
    @pytest.mark.asyncio
    async def test_submit_captures_operation_name(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        mock_client = MagicMock()
        adapter._client = mock_client
        mock_operation = MagicMock()
        mock_operation.name = "operations/generate-videos-xyz789"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                return_value=mock_operation,
            ),
        ):
            job = await adapter.submit_job(_make_prompt())

        assert job.operation_name == "operations/generate-videos-xyz789"

    @pytest.mark.asyncio
    async def test_submit_empty_operation_name_when_none(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        mock_client = MagicMock()
        adapter._client = mock_client
        mock_operation = MagicMock()
        mock_operation.name = None

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                return_value=mock_operation,
            ),
        ):
            job = await adapter.submit_job(_make_prompt())

        assert job.operation_name == ""


# ---------------------------------------------------------------------------
# Task 4: download_clip — success and failure paths
# ---------------------------------------------------------------------------


class TestDownloadClip:
    @pytest.mark.asyncio
    async def test_download_rejects_non_completed(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.GENERATING,
            operation_name="operations/test-op",
        )
        with pytest.raises(Veo3GenerationError, match="Cannot download clip with status"):
            await adapter.download_clip(job, Path("/tmp/test.mp4"))

    @pytest.mark.asyncio
    async def test_download_rejects_empty_operation_name(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.COMPLETED,
            operation_name="",
        )
        with pytest.raises(Veo3GenerationError, match="Cannot download clip without operation_name"):
            await adapter.download_clip(job, Path("/tmp/test.mp4"))

    @pytest.mark.asyncio
    async def test_download_success_writes_file(self, tmp_path: Path) -> None:
        """Successful download writes content to dest via atomic tmp+rename."""
        adapter = GeminiVeo3Adapter(api_key="test-key")
        mock_client = MagicMock()
        adapter._client = mock_client

        # Mock the operation result
        mock_video = MagicMock()
        mock_video.uri = "https://generativelanguage.googleapis.com/v1/files/video123"
        mock_generated = MagicMock()
        mock_generated.video = mock_video
        mock_operation = MagicMock()
        mock_operation.result.generated_videos = [mock_generated]

        # Mock HTTP response
        mock_response = MagicMock()
        video_content = b"fake-video-data-1234567890"
        mock_response.read = MagicMock(side_effect=[video_content, b""])

        dest = tmp_path / "clips" / "broll.mp4"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=[mock_operation, mock_response],
            ),
        ):
            result = await adapter.download_clip(_completed_job(), dest)

        assert result == dest
        assert dest.exists()
        assert dest.read_bytes() == video_content

    @pytest.mark.asyncio
    async def test_download_uses_header_auth(self, tmp_path: Path) -> None:
        """Download uses x-goog-api-key header, not query parameter."""
        adapter = GeminiVeo3Adapter(api_key="secret-api-key-42")
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_video = MagicMock()
        mock_video.uri = "https://generativelanguage.googleapis.com/v1/files/video456"
        mock_generated = MagicMock()
        mock_generated.video = mock_video
        mock_operation = MagicMock()
        mock_operation.result.generated_videos = [mock_generated]

        mock_response = MagicMock()
        mock_response.read = MagicMock(side_effect=[b"data", b""])

        dest = tmp_path / "clip.mp4"
        captured_request = None

        async def mock_to_thread(fn, *args, **kwargs):
            nonlocal captured_request
            # First call is operations.get, second is urlopen
            if hasattr(fn, "__name__") and fn.__name__ == "urlopen":
                # This is urllib.request.urlopen
                captured_request = args[0] if args else kwargs.get("request")
                return mock_response
            if args and hasattr(args[0], "get_header"):
                # This is urllib.request.urlopen with Request object
                captured_request = args[0]
                return mock_response
            return mock_operation

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=mock_to_thread,
            ),
        ):
            await adapter.download_clip(_completed_job(), dest)

        # Verify the Request object was created with the header
        assert captured_request is not None
        assert captured_request.get_header("X-goog-api-key") == "secret-api-key-42"

    @pytest.mark.asyncio
    async def test_download_api_failure_raises_with_chaining(self) -> None:
        """API failure is wrapped in Veo3GenerationError with exception chaining."""
        adapter = GeminiVeo3Adapter(api_key="test-key")
        mock_client = MagicMock()
        adapter._client = mock_client

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=RuntimeError("API unavailable"),
            ),
        ):
            with pytest.raises(Veo3GenerationError, match="Failed to download clip") as exc_info:
                await adapter.download_clip(_completed_job(), Path("/tmp/test.mp4"))
            assert isinstance(exc_info.value.__cause__, RuntimeError)

    @pytest.mark.asyncio
    async def test_download_cleans_tmp_on_failure(self, tmp_path: Path) -> None:
        """Temp file is cleaned up if download fails midway."""
        adapter = GeminiVeo3Adapter(api_key="test-key")
        mock_client = MagicMock()
        adapter._client = mock_client

        mock_video = MagicMock()
        mock_video.uri = "https://example.com/video"
        mock_generated = MagicMock()
        mock_generated.video = mock_video
        mock_operation = MagicMock()
        mock_operation.result.generated_videos = [mock_generated]

        call_count = 0

        async def mock_to_thread(fn, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_operation
            raise ConnectionError("Download interrupted")

        dest = tmp_path / "clip.mp4"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=mock_to_thread,
            ),
            pytest.raises(Veo3GenerationError, match="Failed to download clip"),
        ):
            await adapter.download_clip(_completed_job(), dest)

        # No .tmp files left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0
        assert not dest.exists()


# ---------------------------------------------------------------------------
# Task 5-6: jobs.json round-trip with operation_name
# ---------------------------------------------------------------------------


class TestJobsJsonRoundTrip:
    def test_write_includes_operation_name(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.GENERATING,
                operation_name="operations/gen-abc123",
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs)

        data = json.loads(jobs_path.read_text())
        assert data["jobs"][0]["operation_name"] == "operations/gen-abc123"

    def test_read_parses_operation_name(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs_path.parent.mkdir(parents=True)
        data = {
            "jobs": [
                {
                    "idempotent_key": "run1_broll",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "generating",
                    "operation_name": "operations/gen-def456",
                    "video_path": None,
                    "error_message": None,
                }
            ]
        }
        jobs_path.write_text(json.dumps(data))

        jobs = Veo3Orchestrator._read_jobs_json(jobs_path)
        assert len(jobs) == 1
        assert jobs[0].operation_name == "operations/gen-def456"

    def test_read_defaults_missing_operation_name(self, tmp_path: Path) -> None:
        """Old jobs.json without operation_name defaults to empty string."""
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs_path.parent.mkdir(parents=True)
        data = {
            "jobs": [
                {
                    "idempotent_key": "run1_broll",
                    "variant": "broll",
                    "prompt": "Test",
                    "status": "completed",
                    "video_path": "veo3/broll.mp4",
                    "error_message": None,
                }
            ]
        }
        jobs_path.write_text(json.dumps(data))

        jobs = Veo3Orchestrator._read_jobs_json(jobs_path)
        assert len(jobs) == 1
        assert jobs[0].operation_name == ""

    def test_round_trip_preserves_operation_name(self, tmp_path: Path) -> None:
        """Write then read preserves operation_name."""
        jobs_path = tmp_path / "veo3" / "jobs.json"
        original = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Abstract visualization",
                status=Veo3JobStatus.COMPLETED,
                operation_name="operations/gen-xyz789",
                video_path="veo3/broll.mp4",
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, original)
        restored = Veo3Orchestrator._read_jobs_json(jobs_path)

        assert len(restored) == 1
        assert restored[0].operation_name == "operations/gen-xyz789"
        assert restored[0].idempotent_key == original[0].idempotent_key
        assert restored[0].status == original[0].status
        assert restored[0].video_path == original[0].video_path


# ---------------------------------------------------------------------------
# Task 7: FakeVeo3Adapter operation_name
# ---------------------------------------------------------------------------


class TestFakeAdapterOperationName:
    @pytest.mark.asyncio
    async def test_fake_submit_includes_operation_name(self) -> None:
        fake = FakeVeo3Adapter()
        job = await fake.submit_job(_make_prompt())
        assert job.operation_name == "operations/fake-op-broll"

    @pytest.mark.asyncio
    async def test_fake_submit_operation_name_varies_by_variant(self) -> None:
        fake = FakeVeo3Adapter()
        job_broll = await fake.submit_job(_make_prompt(variant="broll", idempotent_key="r_broll"))
        job_intro = await fake.submit_job(_make_prompt(variant="intro", idempotent_key="r_intro"))
        assert job_broll.operation_name == "operations/fake-op-broll"
        assert job_intro.operation_name == "operations/fake-op-intro"

    @pytest.mark.asyncio
    async def test_fake_poll_preserves_operation_name(self) -> None:
        fake = FakeVeo3Adapter()
        await fake.submit_job(_make_prompt())
        polled = await fake.poll_job("run1_broll")
        assert polled.operation_name == "operations/fake-op-broll"
        assert polled.status == Veo3JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_fake_download_creates_file(self, tmp_path: Path) -> None:
        fake = FakeVeo3Adapter()
        job = _completed_job(operation_name="operations/fake-op-broll")
        dest = tmp_path / "clips" / "broll.mp4"
        result = await fake.download_clip(job, dest)
        assert result == dest
        assert dest.exists()
