"""Tests for face position mapper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "detect_faces.py"
_spec = importlib.util.spec_from_file_location("detect_faces", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["detect_faces"] = _mod
_spec.loader.exec_module(_mod)

detect_faces_in_frames = _mod.detect_faces_in_frames
_classify_side = _mod._classify_side
_spatial_cluster = _mod._spatial_cluster
_extract_timestamp = _mod._extract_timestamp
_check_positions_stable = _mod._check_positions_stable

try:
    import cv2
    import numpy as np

    _HAS_OPENCV = True
except ImportError:
    _HAS_OPENCV = False

pytestmark = pytest.mark.skipif(not _HAS_OPENCV, reason="OpenCV not installed")


def _create_frame(tmp_path: Path, name: str, width: int = 1920, height: int = 1080) -> Path:
    """Create a blank test frame image."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    path = tmp_path / name
    cv2.imwrite(str(path), frame)
    return path


def _create_frame_with_circle(
    tmp_path: Path, name: str, center_x: int, center_y: int, radius: int = 80,
    width: int = 1920, height: int = 1080,
) -> Path:
    """Create a test frame with a circular face-like feature."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    # Draw a skin-toned circle (crude face proxy)
    cv2.circle(frame, (center_x, center_y), radius, (180, 200, 220), -1)
    # Draw eyes (dark circles)
    eye_offset = radius // 3
    cv2.circle(frame, (center_x - eye_offset, center_y - eye_offset), radius // 8, (30, 30, 30), -1)
    cv2.circle(frame, (center_x + eye_offset, center_y - eye_offset), radius // 8, (30, 30, 30), -1)
    path = tmp_path / name
    cv2.imwrite(str(path), frame)
    return path


class TestClassifySide:
    def test_left_classification(self) -> None:
        assert _classify_side(300.0, 1920) == "left"

    def test_right_classification(self) -> None:
        assert _classify_side(1500.0, 1920) == "right"

    def test_center_classification(self) -> None:
        assert _classify_side(960.0, 1920) == "center"

    def test_boundary_left(self) -> None:
        # 0.4 * 1920 = 768
        assert _classify_side(767.0, 1920) == "left"

    def test_boundary_right(self) -> None:
        # 0.6 * 1920 = 1152
        assert _classify_side(1153.0, 1920) == "right"


class TestExtractTimestamp:
    def test_integer_timestamp(self) -> None:
        assert _extract_timestamp("frame_1965.png") == 1965.0

    def test_float_timestamp(self) -> None:
        assert _extract_timestamp("frame_1965.5.png") == 1965.5

    def test_no_match(self) -> None:
        assert _extract_timestamp("random_file.png") is None


class TestSpatialCluster:
    def test_two_clusters(self) -> None:
        faces = [
            {"x": 300, "y": 200, "w": 200, "h": 200, "side": "left"},
            {"x": 320, "y": 210, "w": 190, "h": 190, "side": "left"},
            {"x": 1300, "y": 200, "w": 200, "h": 200, "side": "right"},
            {"x": 1280, "y": 195, "w": 210, "h": 210, "side": "right"},
        ]
        clusters = _spatial_cluster(faces)

        assert len(clusters) == 2
        labels = {c["label"] for c in clusters}
        assert "Speaker_Left" in labels
        assert "Speaker_Right" in labels

    def test_single_cluster(self) -> None:
        faces = [
            {"x": 800, "y": 200, "w": 200, "h": 200, "side": "center"},
            {"x": 810, "y": 210, "w": 190, "h": 190, "side": "center"},
        ]
        clusters = _spatial_cluster(faces)

        assert len(clusters) == 1

    def test_empty_faces(self) -> None:
        assert _spatial_cluster([]) == []


class TestCheckPositionsStable:
    def test_stable_positions(self) -> None:
        faces = [
            {"x": 300, "w": 200},
            {"x": 310, "w": 195},
            {"x": 305, "w": 200},
        ]
        result = _check_positions_stable([1, 1, 1], faces, [{"label": "A"}], 1920)
        assert result is True

    def test_unstable_face_count(self) -> None:
        faces = [{"x": 300, "w": 200}]
        result = _check_positions_stable([1, 2, 1, 3], faces, [{"label": "A"}], 1920)
        assert result is False

    def test_empty_counts(self) -> None:
        result = _check_positions_stable([], [], [], 1920)
        assert result is False


class TestDetectFacesInFrames:
    def test_missing_directory(self, tmp_path: Path) -> None:
        result = detect_faces_in_frames(tmp_path / "nonexistent")

        assert result["frames"] == []
        assert result["summary"]["total_frames"] == 0
        assert "error" in result

    def test_empty_directory(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()

        result = detect_faces_in_frames(frames_dir)

        assert result["frames"] == []
        assert result["summary"]["total_frames"] == 0

    def test_blank_frames_no_faces(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        _create_frame(frames_dir, "frame_100.png")

        result = detect_faces_in_frames(frames_dir)

        assert result["summary"]["total_frames"] == 1
        # Blank frame should have no faces
        frame_data = result["frames"][0]
        assert frame_data["faces"] == []

    def test_result_structure(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        _create_frame(frames_dir, "frame_100.png")

        result = detect_faces_in_frames(frames_dir)

        assert "frames" in result
        assert "summary" in result
        summary = result["summary"]
        assert "total_frames" in summary
        assert "person_count" in summary
        assert "positions_stable" in summary
        assert "speaker_positions" in summary
        assert "detector" in summary

    def test_frame_timestamp_extracted(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        _create_frame(frames_dir, "frame_1965.png")

        result = detect_faces_in_frames(frames_dir)

        assert result["frames"][0]["timestamp"] == 1965.0

    def test_numeric_sort_order(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        # Create frames that would sort differently lexicographically vs numerically
        _create_frame(frames_dir, "frame_9.png")
        _create_frame(frames_dir, "frame_100.png")
        _create_frame(frames_dir, "frame_20.png")

        result = detect_faces_in_frames(frames_dir)

        timestamps = [f.get("timestamp") for f in result["frames"]]
        assert timestamps == [9.0, 20.0, 100.0]

    def test_non_image_files_ignored(self, tmp_path: Path) -> None:
        frames_dir = tmp_path / "frames"
        frames_dir.mkdir()
        _create_frame(frames_dir, "frame_100.png")
        (frames_dir / "notes.txt").write_text("not an image")

        result = detect_faces_in_frames(frames_dir)

        assert result["summary"]["total_frames"] == 1
