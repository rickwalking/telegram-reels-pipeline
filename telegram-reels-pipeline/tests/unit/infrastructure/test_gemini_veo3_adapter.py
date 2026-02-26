"""Tests for GeminiVeo3Adapter and FakeVeo3Adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt
from pipeline.domain.ports import VideoGenerationPort
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


def _adapter_with_mock_client() -> tuple[GeminiVeo3Adapter, MagicMock]:
    adapter = GeminiVeo3Adapter(api_key="test-key")
    mock_client = MagicMock()
    adapter._client = mock_client
    return adapter, mock_client


# ---------------------------------------------------------------------------
# GeminiVeo3Adapter — construction
# ---------------------------------------------------------------------------


class TestGeminiVeo3AdapterConstruction:
    def test_empty_api_key_rejected(self) -> None:
        with pytest.raises(Veo3GenerationError, match="gemini_api_key is required"):
            GeminiVeo3Adapter(api_key="")

    def test_valid_api_key_accepted(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key-123")
        assert adapter._api_key == "test-key-123"
        assert adapter._client is None  # lazy init

    def test_model_id_is_veo3(self) -> None:
        assert GeminiVeo3Adapter.MODEL_ID == "veo-3.1-generate-preview"


# ---------------------------------------------------------------------------
# GeminiVeo3Adapter — lazy client
# ---------------------------------------------------------------------------


class TestGeminiVeo3AdapterClient:
    def test_missing_sdk_raises_generation_error(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        with (
            patch.dict("sys.modules", {"google": None, "google.genai": None}),
            pytest.raises(Veo3GenerationError, match="google-genai SDK not installed"),
        ):
            adapter._get_client()

    def test_client_cached_after_first_call(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        sentinel = MagicMock()
        adapter._client = sentinel
        assert adapter._get_client() is sentinel


# ---------------------------------------------------------------------------
# GeminiVeo3Adapter — submit_job
# ---------------------------------------------------------------------------


class TestGeminiVeo3AdapterSubmitJob:
    @pytest.mark.asyncio
    async def test_submit_job_returns_generating_status(self) -> None:
        adapter, mock_client = _adapter_with_mock_client()
        mock_operation = MagicMock()
        mock_operation.name = "operations/test-op-123"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                return_value=mock_operation,
            ),
        ):
            job = await adapter.submit_job(_make_prompt())

        assert job.status == Veo3JobStatus.GENERATING
        assert job.idempotent_key == "run1_broll"
        assert job.variant == "broll"
        assert job.prompt == "Abstract data visualization"

    @pytest.mark.asyncio
    async def test_submit_job_wraps_exception(self) -> None:
        adapter, _ = _adapter_with_mock_client()

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=RuntimeError("API unavailable"),
            ),
            pytest.raises(Veo3GenerationError, match="Failed to submit Veo3 job"),
        ):
            await adapter.submit_job(_make_prompt())

    @pytest.mark.asyncio
    async def test_submit_job_passes_duration(self) -> None:
        adapter, mock_client = _adapter_with_mock_client()
        mock_operation = MagicMock()
        mock_operation.name = "operations/test-op-456"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                return_value=mock_operation,
            ) as mock_to_thread,
        ):
            await adapter.submit_job(_make_prompt(duration_s=8))
            assert mock_to_thread.call_args[0][0] == mock_client.models.generate_videos

    @pytest.mark.asyncio
    async def test_submit_job_default_duration_when_zero(self) -> None:
        adapter, _ = _adapter_with_mock_client()
        mock_operation = MagicMock()
        mock_operation.name = "operations/test-op-789"

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                return_value=mock_operation,
            ),
        ):
            job = await adapter.submit_job(_make_prompt(duration_s=0))
            assert job.status == Veo3JobStatus.GENERATING

    @pytest.mark.asyncio
    async def test_submit_job_reraises_veo3_error(self) -> None:
        adapter, _ = _adapter_with_mock_client()

        with (
            patch.dict("sys.modules", _GOOGLE_MODULES),
            patch(
                "pipeline.infrastructure.adapters.gemini_veo3_adapter.asyncio.to_thread",
                side_effect=Veo3GenerationError("known error"),
            ),
            pytest.raises(Veo3GenerationError, match="known error"),
        ):
            await adapter.submit_job(_make_prompt())


# ---------------------------------------------------------------------------
# GeminiVeo3Adapter — poll_job
# ---------------------------------------------------------------------------


class TestGeminiVeo3AdapterPollJob:
    @pytest.mark.asyncio
    async def test_poll_job_raises_not_implemented(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        with pytest.raises(NotImplementedError, match="poll_job requires operation state"):
            await adapter.poll_job("run1_broll")


# ---------------------------------------------------------------------------
# GeminiVeo3Adapter — download_clip
# ---------------------------------------------------------------------------


class TestGeminiVeo3AdapterDownloadClip:
    @pytest.mark.asyncio
    async def test_download_rejects_non_completed(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.GENERATING,
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
            video_path="veo3/broll.mp4",
        )
        with pytest.raises(Veo3GenerationError, match="Cannot download clip without operation_name"):
            await adapter.download_clip(job, Path("/tmp/test.mp4"))

    @pytest.mark.asyncio
    async def test_download_rejects_failed_status(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.FAILED,
            error_message="API error",
        )
        with pytest.raises(Veo3GenerationError):
            await adapter.download_clip(job, Path("/tmp/test.mp4"))


# ---------------------------------------------------------------------------
# FakeVeo3Adapter — submit_job
# ---------------------------------------------------------------------------


class TestFakeVeo3AdapterSubmitJob:
    @pytest.mark.asyncio
    async def test_submit_returns_generating(self) -> None:
        fake = FakeVeo3Adapter()
        job = await fake.submit_job(_make_prompt())
        assert job.status == Veo3JobStatus.GENERATING
        assert job.idempotent_key == "run1_broll"
        assert job.variant == "broll"

    @pytest.mark.asyncio
    async def test_submit_tracks_jobs(self) -> None:
        fake = FakeVeo3Adapter()
        await fake.submit_job(_make_prompt())
        await fake.submit_job(_make_prompt(variant="intro", idempotent_key="run1_intro"))
        assert len(fake.submitted_jobs) == 2

    @pytest.mark.asyncio
    async def test_submit_failure_mode(self) -> None:
        fake = FakeVeo3Adapter(fail_on_submit=True)
        with pytest.raises(Veo3GenerationError, match="Fake submit failure"):
            await fake.submit_job(_make_prompt())


# ---------------------------------------------------------------------------
# FakeVeo3Adapter — poll_job
# ---------------------------------------------------------------------------


class TestFakeVeo3AdapterPollJob:
    @pytest.mark.asyncio
    async def test_poll_returns_completed(self) -> None:
        fake = FakeVeo3Adapter()
        await fake.submit_job(_make_prompt())
        job = await fake.poll_job("run1_broll")
        assert job.status == Veo3JobStatus.COMPLETED
        assert job.video_path == "veo3/broll.mp4"

    @pytest.mark.asyncio
    async def test_poll_unknown_key_raises(self) -> None:
        fake = FakeVeo3Adapter()
        with pytest.raises(Veo3GenerationError, match="No job found with key"):
            await fake.poll_job("unknown_key")


# ---------------------------------------------------------------------------
# FakeVeo3Adapter — download_clip
# ---------------------------------------------------------------------------


class TestFakeVeo3AdapterDownloadClip:
    @pytest.mark.asyncio
    async def test_download_creates_file(self, tmp_path: Path) -> None:
        fake = FakeVeo3Adapter()
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.COMPLETED,
            video_path="veo3/broll.mp4",
        )
        dest = tmp_path / "clips" / "broll.mp4"
        result = await fake.download_clip(job, dest)
        assert result == dest
        assert dest.exists()

    @pytest.mark.asyncio
    async def test_download_failure_mode(self, tmp_path: Path) -> None:
        fake = FakeVeo3Adapter(fail_on_download=True)
        job = Veo3Job(
            idempotent_key="run1_broll",
            variant="broll",
            prompt="Test",
            status=Veo3JobStatus.COMPLETED,
            video_path="veo3/broll.mp4",
        )
        with pytest.raises(Veo3GenerationError, match="Fake download failure"):
            await fake.download_clip(job, tmp_path / "clip.mp4")


# ---------------------------------------------------------------------------
# Structural port compliance
# ---------------------------------------------------------------------------


class TestPortCompliance:
    def test_fake_adapter_satisfies_port(self) -> None:
        assert isinstance(FakeVeo3Adapter(), VideoGenerationPort)

    def test_real_adapter_satisfies_port(self) -> None:
        adapter = GeminiVeo3Adapter(api_key="test-key")
        assert isinstance(adapter, VideoGenerationPort)

    def test_veo3_generation_error_is_pipeline_error(self) -> None:
        from pipeline.domain.errors import PipelineError

        assert issubclass(Veo3GenerationError, PipelineError)
