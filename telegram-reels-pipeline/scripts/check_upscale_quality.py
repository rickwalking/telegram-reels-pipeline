"""Quality degradation checker — validates upscale factor and sharpness of encoded segments.

Checks whether cropping and upscaling produces acceptable visual quality. Supports
both post-encode validation (with actual segment) and pre-encode prediction (from
crop dimensions alone).

Usage::

    # Post-encode check
    python scripts/check_upscale_quality.py <segment_path> --crop-width 608 --target-width 1080

    # Pre-encode prediction (no segment needed)
    python scripts/check_upscale_quality.py --predict --crop-width 608 --target-width 1080

    # With source baseline for sharpness comparison
    python scripts/check_upscale_quality.py <segment> --crop-width 608 --target-width 1080 --source-frame source.png
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    import cv2
    import numpy as np

    _HAS_OPENCV = True
except ImportError:
    _HAS_OPENCV = False


def _classify_quality(upscale_factor: float) -> str:
    """Classify quality based on upscale factor."""
    if upscale_factor <= 1.2:
        return "good"
    elif upscale_factor <= 1.5:
        return "acceptable"
    elif upscale_factor <= 2.0:
        return "degraded"
    return "unacceptable"


def _recommend_action(quality: str) -> str:
    """Recommend action based on quality classification."""
    if quality in ("good", "acceptable"):
        return "proceed"
    elif quality == "degraded":
        return "widen_crop"
    return "use_pillarbox"


def _compute_sharpness(frame: np.ndarray) -> float:
    """Compute sharpness using variance of Laplacian."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def _extract_frames_from_segment(segment_path: Path, count: int = 3) -> list[np.ndarray]:
    """Extract evenly-spaced frames from a video segment using sequential reads.

    Uses sequential reading with frame skipping instead of seeking, which is
    more reliable and faster on Raspberry Pi hardware.
    """
    if not _HAS_OPENCV:
        return []

    cap = cv2.VideoCapture(str(segment_path))
    if not cap.isOpened():
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        cap.release()
        return []

    # Calculate frame indices evenly spaced
    if total_frames <= count:
        target_indices = set(range(total_frames))
    else:
        step = total_frames / (count + 1)
        target_indices = {int(step * (i + 1)) for i in range(count)}

    # Sequential read — grab/skip frames until we have what we need
    frames: list[np.ndarray] = []
    frame_idx = 0
    max_target = max(target_indices)

    while frame_idx <= max_target:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx in target_indices:
            frames.append(frame)
        frame_idx += 1

    cap.release()
    return frames


def _apply_sharpness_baseline(
    result: dict[str, object],
    sharpness_avg: float,
    source_frame_path: Path,
    quality: str,
) -> None:
    """Adjust quality based on sharpness ratio against source baseline (mutates result)."""
    source_frame = cv2.imread(str(source_frame_path))
    if source_frame is None:
        return

    baseline = _compute_sharpness(source_frame)
    ratio = sharpness_avg / baseline if baseline > 0 else 0.0
    result["baseline_sharpness"] = round(baseline, 2)
    result["sharpness_ratio"] = round(ratio, 3)

    if ratio < 0.4:
        result["quality"] = "unacceptable"
        result["recommendation"] = "use_pillarbox"
    elif ratio < 0.6 and quality in ("good", "acceptable"):
        result["quality"] = "degraded"
        result["recommendation"] = "accept_with_penalty"


def check_upscale_quality(
    segment_path: Path | None,
    crop_width: int,
    target_width: int,
    source_frame_path: Path | None = None,
    predict_only: bool = False,
) -> dict[str, object]:
    """Check quality degradation from cropping and upscaling.

    Args:
        segment_path: Path to encoded segment (None for predict mode).
        crop_width: Original crop width before scaling.
        target_width: Target width after scaling (typically 1080).
        source_frame_path: Optional source frame for sharpness baseline.
        predict_only: If True, only compute upscale factor prediction.

    Returns:
        Quality check results with upscale factor, quality, sharpness, and recommendation.
    """
    if crop_width <= 0 or target_width <= 0:
        return {
            "upscale_factor": 999.0,
            "quality": "unacceptable",
            "crop_width": crop_width,
            "target_width": target_width,
            "recommendation": "use_pillarbox",
            "error": f"Invalid dimensions: crop_width={crop_width}, target_width={target_width}",
        }
    upscale_factor = target_width / crop_width
    quality = _classify_quality(upscale_factor)
    recommendation = _recommend_action(quality)

    result: dict[str, object] = {
        "upscale_factor": round(upscale_factor, 3),
        "quality": quality,
        "crop_width": crop_width,
        "target_width": target_width,
        "recommendation": recommendation,
    }

    if predict_only:
        result["mode"] = "predict"
        return result

    if not _HAS_OPENCV:
        result["error"] = "OpenCV not installed — sharpness check skipped"
        result["mode"] = "predict"
        return result

    if segment_path is None or not segment_path.exists():
        result["error"] = f"Segment not found: {segment_path}"
        result["mode"] = "predict"
        return result

    frames = _extract_frames_from_segment(segment_path)
    if not frames:
        result["error"] = "Failed to extract frames from segment"
        result["mode"] = "predict"
        return result

    sharpness_values = [_compute_sharpness(f) for f in frames]
    sharpness_avg = sum(sharpness_values) / len(sharpness_values)

    result["mode"] = "full"
    result["sharpness_avg"] = round(sharpness_avg, 2)
    result["sharpness_per_frame"] = [round(v, 2) for v in sharpness_values]
    result["frames_checked"] = len(frames)

    if source_frame_path is not None and source_frame_path.exists():
        _apply_sharpness_baseline(result, sharpness_avg, source_frame_path, quality)

    return result


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
    parser = argparse.ArgumentParser(description="Check quality degradation from crop+upscale")
    parser.add_argument("segment_path", nargs="?", type=Path, default=None, help="Path to encoded segment")
    parser.add_argument("--crop-width", type=int, required=True, help="Original crop width before scaling")
    parser.add_argument("--target-width", type=int, default=1080, help="Target width after scaling (default: 1080)")
    parser.add_argument("--source-frame", type=Path, default=None, help="Source frame for sharpness baseline")
    parser.add_argument(
        "--predict", action="store_true", help="Predict quality from dimensions only (no segment needed)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Output path (default: stdout)")
    args = parser.parse_args()

    if not args.predict and args.segment_path is None:
        parser.error("segment_path is required unless --predict is used")

    result = check_upscale_quality(
        segment_path=args.segment_path,
        crop_width=args.crop_width,
        target_width=args.target_width,
        source_frame_path=args.source_frame,
        predict_only=args.predict,
    )

    if args.output:
        _atomic_write_json(result, args.output)
        print(
            f"Quality check written to {args.output} "
            f"(factor: {result['upscale_factor']}x, quality: {result['quality']})",
            file=sys.stderr,
        )
    else:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
