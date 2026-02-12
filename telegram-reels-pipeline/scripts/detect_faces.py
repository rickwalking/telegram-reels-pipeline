"""Full-frame face position mapper — proactive intelligence for crop decisions.

Scans all extracted frames with YuNet DNN face detection to build a face position
map BEFORE any crop decisions are made. Produces face-position-map.json with
per-frame face positions and a summary of speaker positions via spatial clustering.

Usage::

    python scripts/detect_faces.py <frames_dir> [--output path] [--min-confidence 0.7] [--min-face-width 50]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import cv2
    import numpy as np

    _HAS_OPENCV = True
except ImportError:
    _HAS_OPENCV = False

# Timestamp extraction from frame filenames like "frame_1965.png" or "frame_1965.0.png"
_FRAME_TS_PATTERN = re.compile(r"frame_(\d+(?:\.\d+)?)")

# YuNet model filename (bundled with OpenCV >= 4.5.4)
_YUNET_MODEL = "face_detection_yunet_2023mar.onnx"


def _extract_timestamp(filename: str) -> float | None:
    """Extract timestamp from frame filename (e.g., 'frame_1965.png' -> 1965.0)."""
    m = _FRAME_TS_PATTERN.search(filename)
    return float(m.group(1)) if m else None


def _find_yunet_model() -> str | None:
    """Find YuNet ONNX model file. Checks common OpenCV data paths."""
    # Check alongside this script
    script_dir = Path(__file__).parent
    local_model = script_dir / _YUNET_MODEL
    if local_model.exists():
        return str(local_model)

    # Check OpenCV data directory
    if _HAS_OPENCV:
        cv_data = getattr(cv2, "data", None)
        if cv_data:
            data_dir = getattr(cv_data, "haarcascades", "")
            if data_dir:
                model_path = Path(data_dir).parent / _YUNET_MODEL
                if model_path.exists():
                    return str(model_path)

    return None


def _create_face_detector(
    frame_width: int,
    frame_height: int,
    min_confidence: float,
) -> object | None:
    """Create YuNet face detector. Returns None if unavailable."""
    if not _HAS_OPENCV:
        return None

    model_path = _find_yunet_model()
    if model_path is None:
        return None

    try:
        detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (frame_width, frame_height),
            min_confidence,
            0.3,  # NMS threshold
        )
        return detector
    except cv2.error:
        return None


def _detect_faces_yunet(
    frame: np.ndarray,
    detector: object,
    min_face_width: int,
) -> list[dict[str, object]]:
    """Detect faces using YuNet DNN detector."""
    _, detections = detector.detect(frame)  # type: ignore[union-attr]
    if detections is None:
        return []

    faces: list[dict[str, object]] = []
    for det in detections:
        x, y, w, h = int(det[0]), int(det[1]), int(det[2]), int(det[3])
        conf = float(det[-1])
        if w < min_face_width:
            continue
        faces.append({"x": x, "y": y, "w": w, "h": h, "confidence": round(conf, 3)})
    return faces


def _get_haar_cascade() -> object | None:
    """Get or create the singleton Haar cascade classifier."""
    if not _HAS_OPENCV:
        return None
    if not hasattr(_get_haar_cascade, "_instance"):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore[attr-defined]
        _get_haar_cascade._instance = cv2.CascadeClassifier(cascade_path)  # type: ignore[attr-defined]
    return _get_haar_cascade._instance  # type: ignore[attr-defined]


def _detect_faces_haar(
    frame: np.ndarray,
    min_face_width: int,
    min_confidence: float,
) -> list[dict[str, object]]:
    """Fallback: detect faces using Haar cascade."""
    cascade = _get_haar_cascade()
    if cascade is None:
        return []

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    min_size = (min_face_width, min_face_width)
    detections = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=min_size)

    faces: list[dict[str, object]] = []
    for x, y, w, h in detections:
        faces.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "confidence": round(min_confidence, 3)})
    return faces


def _classify_side(center_x: float, frame_width: int) -> str:
    """Classify face position as left/center/right."""
    ratio = center_x / frame_width
    if ratio < 0.4:
        return "left"
    elif ratio > 0.6:
        return "right"
    return "center"


def _spatial_cluster(
    all_faces: list[dict[str, object]],
    cluster_threshold: float = 200.0,
) -> list[dict[str, object]]:
    """Cluster face detections across frames by X position.

    Uses simple Euclidean distance on X centroids. Faces within
    cluster_threshold pixels are considered the same speaker.

    Returns list of speaker position summaries.
    """
    if not all_faces:
        return []

    # Collect all centroids
    centroids: list[tuple[float, float, str]] = []
    for face in all_faces:
        cx = face["x"] + face["w"] / 2  # type: ignore[operator]
        cy = face["y"] + face["h"] / 2  # type: ignore[operator]
        side = face.get("side", "center")
        centroids.append((cx, cy, str(side)))

    # Simple 1D clustering on X position
    sorted_centroids = sorted(centroids, key=lambda c: c[0])
    clusters: list[list[tuple[float, float, str]]] = []
    current_cluster: list[tuple[float, float, str]] = [sorted_centroids[0]]

    for cx, cy, side in sorted_centroids[1:]:
        cluster_avg_x = sum(c[0] for c in current_cluster) / len(current_cluster)
        if abs(cx - cluster_avg_x) <= cluster_threshold:
            current_cluster.append((cx, cy, side))
        else:
            clusters.append(current_cluster)
            current_cluster = [(cx, cy, side)]
    clusters.append(current_cluster)

    # Build speaker summaries
    speakers: list[dict[str, object]] = []
    side_labels = {"left": "Speaker_Left", "right": "Speaker_Right", "center": "Speaker_Center"}

    for cluster in clusters:
        avg_x = sum(c[0] for c in cluster) / len(cluster)
        avg_y = sum(c[1] for c in cluster) / len(cluster)
        # Most common side in cluster
        side_counts: dict[str, int] = {}
        for _, _, s in cluster:
            side_counts[s] = side_counts.get(s, 0) + 1
        dominant_side = max(side_counts, key=side_counts.get)  # type: ignore[arg-type]
        label = side_labels.get(dominant_side, f"Speaker_{dominant_side.title()}")

        speakers.append({
            "label": label,
            "avg_x": round(avg_x, 1),
            "avg_y": round(avg_y, 1),
            "seen_in_frames": len(cluster),
        })

    return speakers


def _empty_face_result(**extra: object) -> dict[str, object]:
    """Return an empty face detection result."""
    result: dict[str, object] = {
        "frames": [],
        "summary": {
            "total_frames": 0,
            "person_count": 0,
            "positions_stable": False,
            "speaker_positions": [],
        },
    }
    result.update(extra)
    return result


def _process_frame(
    frame_file: Path,
    detector: object | None,
    use_yunet: bool,
    min_face_width: int,
    min_confidence: float,
    ref_width: int,
    ref_height: int,
) -> tuple[dict[str, object], list[dict[str, object]]] | None:
    """Process a single frame file for face detections."""
    timestamp = _extract_timestamp(frame_file.name)
    frame = cv2.imread(str(frame_file))
    if frame is None:
        return None

    h, w = frame.shape[:2]
    if use_yunet and detector is not None and (w != ref_width or h != ref_height):
        detector.setInputSize((w, h))  # type: ignore[union-attr]

    if use_yunet and detector is not None:
        faces = _detect_faces_yunet(frame, detector, min_face_width)
    else:
        faces = _detect_faces_haar(frame, min_face_width, min_confidence)

    for face in faces:
        center_x = face["x"] + face["w"] / 2  # type: ignore[operator]
        face["side"] = _classify_side(center_x, w)

    frame_entry: dict[str, object] = {"frame_path": frame_file.name, "faces": faces}
    if timestamp is not None:
        frame_entry["timestamp"] = timestamp

    return frame_entry, list(faces)


def _check_positions_stable(
    face_counts: list[int],
    all_faces: list[dict[str, object]],
    speaker_positions: list[dict[str, object]],
    frame_width: int,
) -> bool:
    """Check if face positions are stable across frames."""
    count_stable = len(set(face_counts)) <= 2 if face_counts else False

    x_variance_stable = True
    if speaker_positions and all_faces:
        x_positions = [float(f["x"]) + float(f["w"]) / 2 for f in all_faces]  # type: ignore[arg-type]
        if len(x_positions) >= 2:
            mean_x = sum(x_positions) / len(x_positions)
            variance = sum((x - mean_x) ** 2 for x in x_positions) / len(x_positions)
            x_variance_stable = variance < (frame_width * 0.15) ** 2

    return count_stable and x_variance_stable


def detect_faces_in_frames(
    frames_dir: Path,
    min_confidence: float = 0.7,
    min_face_width: int = 50,
) -> dict[str, object]:
    """Detect faces in all frames in a directory and build a face position map.

    Args:
        frames_dir: Directory containing extracted frame images.
        min_confidence: Minimum detection confidence (0-1).
        min_face_width: Minimum face width in pixels.

    Returns:
        Face position map with per-frame data and summary.
    """
    if not _HAS_OPENCV:
        return _empty_face_result(error="OpenCV not installed. Install with: pip install opencv-python-headless")

    if not frames_dir.is_dir():
        return _empty_face_result(error=f"Frames directory not found: {frames_dir}")

    frame_files = sorted(
        [f for f in frames_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg")],
        key=lambda f: _extract_timestamp(f.name) or 0.0,
    )
    if not frame_files:
        return _empty_face_result()

    first_frame = cv2.imread(str(frame_files[0]))
    if first_frame is None:
        return _empty_face_result(error=f"Failed to read frame: {frame_files[0]}")

    frame_height, frame_width = first_frame.shape[:2]
    detector = _create_face_detector(frame_width, frame_height, min_confidence)
    use_yunet = detector is not None
    if not use_yunet:
        print("WARNING: YuNet model not found, falling back to Haar cascade", file=sys.stderr)

    frame_results: list[dict[str, object]] = []
    all_face_detections: list[dict[str, object]] = []

    for frame_file in frame_files:
        result = _process_frame(
            frame_file, detector, use_yunet, min_face_width, min_confidence, frame_width, frame_height,
        )
        if result is not None:
            frame_entry, faces = result
            frame_results.append(frame_entry)
            all_face_detections.extend(faces)

    speaker_positions = _spatial_cluster(all_face_detections)
    face_counts = [len(fr["faces"]) for fr in frame_results]  # type: ignore[arg-type]
    positions_stable = _check_positions_stable(face_counts, all_face_detections, speaker_positions, frame_width)

    return {
        "frames": frame_results,
        "summary": {
            "total_frames": len(frame_results),
            "person_count": len(speaker_positions),
            "positions_stable": positions_stable,
            "speaker_positions": speaker_positions,
            "detector": "yunet" if use_yunet else "haar_cascade",
        },
    }


def _atomic_write_json(data: object, output_path: Path) -> None:
    """Write JSON atomically (write-to-tmp + rename)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, output_path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect faces in extracted frames and build position map")
    parser.add_argument("frames_dir", type=Path, help="Directory containing extracted frame images")
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: stdout)")
    parser.add_argument("--min-confidence", type=float, default=0.7, help="Minimum detection confidence (default: 0.7)")
    parser.add_argument("--min-face-width", type=int, default=50, help="Minimum face width in pixels (default: 50)")
    args = parser.parse_args()

    result = detect_faces_in_frames(
        args.frames_dir,
        min_confidence=args.min_confidence,
        min_face_width=args.min_face_width,
    )

    if args.output:
        _atomic_write_json(result, args.output)
        summary = result.get("summary", {})
        print(
            f"Face position map written to {args.output} "
            f"({summary.get('total_frames', 0)} frames, {summary.get('person_count', 0)} persons)",
            file=sys.stderr,
        )
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
