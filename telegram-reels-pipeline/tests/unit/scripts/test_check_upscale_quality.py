"""Tests for quality degradation checker."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "check_upscale_quality.py"
_spec = importlib.util.spec_from_file_location("check_upscale_quality", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["check_upscale_quality"] = _mod
_spec.loader.exec_module(_mod)

check_upscale_quality = _mod.check_upscale_quality
_classify_quality = _mod._classify_quality
_recommend_action = _mod._recommend_action

try:
    import cv2
    import numpy as np

    _HAS_OPENCV = True
except ImportError:
    _HAS_OPENCV = False


class TestClassifyQuality:
    def test_good_at_1x(self) -> None:
        assert _classify_quality(1.0) == "good"

    def test_good_at_boundary(self) -> None:
        assert _classify_quality(1.2) == "good"

    def test_acceptable(self) -> None:
        assert _classify_quality(1.3) == "acceptable"

    def test_acceptable_at_boundary(self) -> None:
        assert _classify_quality(1.5) == "acceptable"

    def test_degraded(self) -> None:
        assert _classify_quality(1.7) == "degraded"

    def test_degraded_at_boundary(self) -> None:
        assert _classify_quality(2.0) == "degraded"

    def test_unacceptable(self) -> None:
        assert _classify_quality(2.5) == "unacceptable"


class TestRecommendAction:
    def test_good_proceed(self) -> None:
        assert _recommend_action("good") == "proceed"

    def test_acceptable_proceed(self) -> None:
        assert _recommend_action("acceptable") == "proceed"

    def test_degraded_widen(self) -> None:
        assert _recommend_action("degraded") == "widen_crop"

    def test_unacceptable_pillarbox(self) -> None:
        assert _recommend_action("unacceptable") == "use_pillarbox"


class TestCheckUpscaleQualityPredictMode:
    def test_predict_good_quality(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=960, target_width=1080, predict_only=True,
        )

        assert result["mode"] == "predict"
        assert result["quality"] == "good"
        assert result["upscale_factor"] == 1.125
        assert result["recommendation"] == "proceed"

    def test_predict_degraded_quality(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=608, target_width=1080, predict_only=True,
        )

        assert result["quality"] == "degraded"
        assert result["recommendation"] == "widen_crop"
        assert result["upscale_factor"] == pytest.approx(1.776, abs=0.001)

    def test_predict_unacceptable_quality(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=400, target_width=1080, predict_only=True,
        )

        assert result["quality"] == "unacceptable"
        assert result["recommendation"] == "use_pillarbox"

    def test_predict_exact_boundaries(self) -> None:
        # 1.2x boundary
        result = check_upscale_quality(
            segment_path=None, crop_width=900, target_width=1080, predict_only=True,
        )
        assert result["quality"] == "good"  # 1080/900 = 1.2

        # 1.5x boundary
        result = check_upscale_quality(
            segment_path=None, crop_width=720, target_width=1080, predict_only=True,
        )
        assert result["quality"] == "acceptable"  # 1080/720 = 1.5

        # 2.0x boundary
        result = check_upscale_quality(
            segment_path=None, crop_width=540, target_width=1080, predict_only=True,
        )
        assert result["quality"] == "degraded"  # 1080/540 = 2.0


class TestInvalidDimensions:
    def test_zero_crop_width(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=0, target_width=1080, predict_only=True,
        )

        assert result["quality"] == "unacceptable"
        assert result["recommendation"] == "use_pillarbox"
        assert "error" in result

    def test_negative_crop_width(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=-100, target_width=1080, predict_only=True,
        )

        assert result["quality"] == "unacceptable"
        assert "error" in result

    def test_negative_target_width(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=960, target_width=-1, predict_only=True,
        )

        assert result["quality"] == "unacceptable"
        assert "error" in result

    def test_zero_target_width(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=960, target_width=0, predict_only=True,
        )

        assert result["quality"] == "unacceptable"
        assert "error" in result


class TestSegmentNotFound:
    def test_missing_segment(self, tmp_path: Path) -> None:
        result = check_upscale_quality(
            segment_path=tmp_path / "nonexistent.mp4",
            crop_width=960,
            target_width=1080,
        )

        assert result["mode"] == "predict"
        assert "error" in result

    def test_none_segment(self) -> None:
        result = check_upscale_quality(
            segment_path=None,
            crop_width=960,
            target_width=1080,
        )

        assert result["mode"] == "predict"
        assert "error" in result


class TestResultStructure:
    def test_predict_mode_keys(self) -> None:
        result = check_upscale_quality(
            segment_path=None, crop_width=960, target_width=1080, predict_only=True,
        )

        assert "upscale_factor" in result
        assert "quality" in result
        assert "crop_width" in result
        assert "target_width" in result
        assert "recommendation" in result
        assert "mode" in result

    @pytest.mark.skipif(not _HAS_OPENCV, reason="OpenCV required for sharpness tests")
    def test_full_mode_keys_with_frames(self, tmp_path: Path) -> None:
        # Create a simple test video with ffmpeg would be complex,
        # so test the fallback path when segment can't be read
        segment = tmp_path / "test.mp4"
        segment.write_bytes(b"not a real video")

        result = check_upscale_quality(
            segment_path=segment, crop_width=960, target_width=1080,
        )

        # Should fall back to predict mode since frames can't be extracted
        assert result["mode"] == "predict"
        assert "error" in result


@pytest.mark.skipif(not _HAS_OPENCV, reason="OpenCV required for sharpness tests")
class TestSharpness:
    def test_sharp_image_has_higher_sharpness(self, tmp_path: Path) -> None:
        from check_upscale_quality import _compute_sharpness

        # Create sharp image (high contrast edges)
        sharp = np.zeros((100, 100, 3), dtype=np.uint8)
        sharp[::2, :] = 255  # Alternating black/white rows = very sharp
        sharp_score = _compute_sharpness(sharp)

        # Create blurry image
        blurry = cv2.GaussianBlur(sharp, (21, 21), 10)
        blurry_score = _compute_sharpness(blurry)

        assert sharp_score > blurry_score
        assert sharp_score > 0
        assert blurry_score >= 0
