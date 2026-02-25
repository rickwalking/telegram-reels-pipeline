"""Tests for Veo3PostProcessor — watermark crop and clip quality validation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.infrastructure.adapters.veo3_postprocessor import (
    Veo3PostProcessError,
    Veo3PostProcessor,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_process(
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
) -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


def _ffprobe_stdout(width: int = 1080, height: int = 1936, duration: float = 8.0) -> bytes:
    """Build a minimal ffprobe JSON response for a video stream."""
    payload = {
        "streams": [
            {
                "width": width,
                "height": height,
                "duration": str(duration),
            }
        ]
    }
    return json.dumps(payload).encode()


# ---------------------------------------------------------------------------
# TestBuildCropFilter
# ---------------------------------------------------------------------------

class TestBuildCropFilter:
    def test_default_16px(self) -> None:
        processor = Veo3PostProcessor()
        assert processor.build_crop_filter() == "crop=in_w:in_h-16:0:0"

    def test_custom_32px(self) -> None:
        processor = Veo3PostProcessor(crop_bottom_px=32)
        assert processor.build_crop_filter() == "crop=in_w:in_h-32:0:0"

    def test_zero_px(self) -> None:
        processor = Veo3PostProcessor(crop_bottom_px=0)
        assert processor.build_crop_filter() == "crop=in_w:in_h-0:0:0"

    def test_filter_contains_in_w(self) -> None:
        processor = Veo3PostProcessor(crop_bottom_px=8)
        f = processor.build_crop_filter()
        assert "in_w" in f
        assert "in_h" in f

    def test_filter_format(self) -> None:
        processor = Veo3PostProcessor(crop_bottom_px=20)
        # Must be crop=in_w:in_h-{px}:0:0
        assert processor.build_crop_filter() == "crop=in_w:in_h-20:0:0"


# ---------------------------------------------------------------------------
# TestCheckAspectRatio
# ---------------------------------------------------------------------------

class TestCheckAspectRatio:
    def test_exact_9_16(self) -> None:
        # 1080x1920 = exactly 9:16
        assert Veo3PostProcessor._check_aspect_ratio(1080, 1920) is True

    def test_within_tolerance(self) -> None:
        # 1080x1904 -> 1080/1904 ≈ 0.5672 (delta ≈ 0.0047 < 0.01)
        assert Veo3PostProcessor._check_aspect_ratio(1080, 1904) is True

    def test_outside_tolerance(self) -> None:
        # 1080x1080 -> ratio 1.0, far from 0.5625
        assert Veo3PostProcessor._check_aspect_ratio(1080, 1080) is False

    def test_zero_height_returns_false(self) -> None:
        assert Veo3PostProcessor._check_aspect_ratio(1080, 0) is False

    def test_borderline_just_inside(self) -> None:
        # 1080/1921 ≈ 0.56220 -> delta ≈ 0.0003 < 0.01
        assert Veo3PostProcessor._check_aspect_ratio(1080, 1921) is True

    def test_borderline_just_outside(self) -> None:
        # Wide 16:9 landscape — 1920x1080 = ratio ≈ 1.777
        assert Veo3PostProcessor._check_aspect_ratio(1920, 1080) is False


# ---------------------------------------------------------------------------
# TestCheckDuration
# ---------------------------------------------------------------------------

class TestCheckDuration:
    def test_exact_match(self) -> None:
        assert Veo3PostProcessor._check_duration(8.0, 8) is True

    def test_within_1s_below(self) -> None:
        assert Veo3PostProcessor._check_duration(7.0, 8) is True

    def test_within_1s_above(self) -> None:
        assert Veo3PostProcessor._check_duration(9.0, 8) is True

    def test_exactly_at_lower_boundary(self) -> None:
        assert Veo3PostProcessor._check_duration(7.0, 8) is True

    def test_exactly_at_upper_boundary(self) -> None:
        assert Veo3PostProcessor._check_duration(9.0, 8) is True

    def test_just_outside_lower(self) -> None:
        assert Veo3PostProcessor._check_duration(6.9, 8) is False

    def test_just_outside_upper(self) -> None:
        assert Veo3PostProcessor._check_duration(9.1, 8) is False

    def test_zero_expected(self) -> None:
        # 0.5s actual vs 0s expected: abs(0.5-0)=0.5 <= 1.0 -> passes
        assert Veo3PostProcessor._check_duration(0.5, 0) is True
        # 0.0s actual vs 0s expected: exact match
        assert Veo3PostProcessor._check_duration(0.0, 0) is True
        # 2.0s actual vs 0s expected: abs(2.0-0)=2.0 > 1.0 -> fails
        assert Veo3PostProcessor._check_duration(2.0, 0) is False


# ---------------------------------------------------------------------------
# TestCropAndValidate — happy path
# ---------------------------------------------------------------------------

class TestCropAndValidateHappyPath:
    async def test_passes_valid_clip(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"fake-video")

        # ffprobe response: 1080x1936, 8s (after crop: 1080x1920 = 9:16)
        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.0))
        # FFmpeg crop — also creates the .tmp.mp4
        crop_proc = _mock_process()
        # blackdetect — no black_start in stderr
        black_proc = _mock_process(stderr=b"nothing here")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            # Create the .tmp.mp4 that would be produced by FFmpeg
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"cropped-video")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is True

    async def test_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        processor = Veo3PostProcessor()
        result = await processor.crop_and_validate(
            tmp_path / "nonexistent.mp4", expected_duration_s=8
        )
        assert result is False

    async def test_returns_false_on_ffprobe_failure(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        probe_proc = _mock_process(returncode=1, stderr=b"ffprobe error")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=probe_proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False

    async def test_returns_false_on_ffmpeg_crop_failure(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.0))
        crop_proc = _mock_process(returncode=1, stderr=b"crop error")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False
        # tmp file should be cleaned up
        assert not clip.with_suffix(".tmp.mp4").exists()


# ---------------------------------------------------------------------------
# TestCropAndValidate — validation failures
# ---------------------------------------------------------------------------

class TestCropAndValidateAspectRatioFailure:
    async def test_fails_wrong_aspect_ratio(self, tmp_path: Path) -> None:
        """A 1080x1080 clip (1:1) must fail the 9:16 check."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        # height=1080, crop_bottom_px=16 -> cropped height=1064
        # 1080/1064 ≈ 1.015 — far from 0.5625
        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1080, 8.0))
        crop_proc = _mock_process()
        black_proc = _mock_process(stderr=b"")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False


class TestCropAndValidateDurationFailure:
    async def test_fails_duration_too_short(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        # duration=5.0, expected=8, delta=3 > 1
        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 5.0))
        crop_proc = _mock_process()
        black_proc = _mock_process(stderr=b"")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False

    async def test_fails_duration_too_long(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        # duration=15.0, expected=8, delta=7 > 1
        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 15.0))
        crop_proc = _mock_process()
        black_proc = _mock_process(stderr=b"")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False


class TestCropAndValidateBlackFrameFailure:
    async def test_fails_when_black_frames_detected(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.0))
        crop_proc = _mock_process()
        # Simulate FFmpeg blackdetect output containing a detection
        black_stderr = b"[blackdetect @ 0x...] black_start:1.0 black_end:2.0 black_duration:1.0"
        black_proc = _mock_process(stderr=black_stderr)

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is False

    async def test_passes_when_no_black_frames(self, tmp_path: Path) -> None:
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.0))
        crop_proc = _mock_process()
        # No black_start in stderr
        black_proc = _mock_process(stderr=b"frame=  240 fps= 30 q=-0.0 Lsize=N/A")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is True

    async def test_blackdetect_failure_does_not_reject_clip(self, tmp_path: Path) -> None:
        """If blackdetect itself fails, do not reject — just skip the black-frame check."""
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"data")

        probe_proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.0))
        crop_proc = _mock_process()
        # blackdetect exits non-zero — treated conservatively as no black frames
        black_proc = _mock_process(returncode=1, stderr=b"probe error")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                side_effect=[probe_proc, crop_proc, black_proc]
            )
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor(crop_bottom_px=16)
            tmp_out = clip.with_suffix(".tmp.mp4")
            tmp_out.write_bytes(b"data")

            result = await processor.crop_and_validate(clip, expected_duration_s=8)

        assert result is True


# ---------------------------------------------------------------------------
# TestProbeClip
# ---------------------------------------------------------------------------

class TestProbeClip:
    async def test_raises_on_nonzero_returncode(self, tmp_path: Path) -> None:
        proc = _mock_process(returncode=1, stderr=b"probe error")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            with pytest.raises(Veo3PostProcessError, match="ffprobe exited"):
                await processor._probe_clip(tmp_path / "clip.mp4")

    async def test_raises_on_empty_streams(self, tmp_path: Path) -> None:
        payload = json.dumps({"streams": []}).encode()
        proc = _mock_process(stdout=payload)

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            with pytest.raises(Veo3PostProcessError, match="no video streams"):
                await processor._probe_clip(tmp_path / "clip.mp4")

    async def test_raises_on_invalid_json(self, tmp_path: Path) -> None:
        proc = _mock_process(stdout=b"not-json")

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            with pytest.raises(Veo3PostProcessError, match="Could not parse"):
                await processor._probe_clip(tmp_path / "clip.mp4")

    async def test_returns_width_height_duration(self, tmp_path: Path) -> None:
        proc = _mock_process(stdout=_ffprobe_stdout(1080, 1936, 8.5))

        with patch(
            "pipeline.infrastructure.adapters.veo3_postprocessor.asyncio"
        ) as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=proc)
            mock_aio.subprocess = __import__("asyncio").subprocess

            processor = Veo3PostProcessor()
            width, height, duration = await processor._probe_clip(tmp_path / "clip.mp4")

        assert width == 1080
        assert height == 1936
        assert duration == pytest.approx(8.5)
