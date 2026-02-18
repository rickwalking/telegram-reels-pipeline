"""OCR for screen share frames — extract text from slides, code, and demos.

Requires Tesseract: ``apt install tesseract-ocr``
Pi-conditional: only run if benchmark gate (12-4) shows sufficient headroom.

Usage::

    poetry run python scripts/ocr_screen_share.py <frames_dir> \\
        --output <workspace>/screen-share-ocr.json \\
        --confidence 60
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrameOCRResult:
    """OCR result for a single frame."""

    frame_path: str
    timestamp: float
    text: str
    confidence: float
    word_count: int


def _timestamp_from_filename(path: Path) -> float:
    """Extract timestamp from frame filename like 'frame_1260.png' or 'frame_1260.5.png'."""
    stem = path.stem
    # Remove 'frame_' prefix
    if stem.startswith("frame_"):
        stem = stem[len("frame_") :]
    try:
        return float(stem)
    except ValueError:
        return 0.0


def _check_tesseract() -> bool:
    """Check if tesseract is available on the system."""
    import shutil

    return shutil.which("tesseract") is not None


def _parse_tsv_words(
    lines: list[str],
    min_confidence: float,
) -> tuple[list[str], list[float]]:
    """Parse Tesseract TSV output lines into words and confidence scores."""
    words: list[str] = []
    confidences: list[float] = []
    for line in lines[1:]:  # Skip header
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        conf_str = parts[10].strip()
        text = parts[11].strip()
        if not text or conf_str == "-1":
            continue
        try:
            conf = float(conf_str)
        except ValueError:
            continue
        if conf >= min_confidence:
            words.append(text)
            confidences.append(conf)
    return words, confidences


def _run_tesseract(frame_path: Path) -> list[str] | None:
    """Run tesseract on a frame and return TSV lines, or None on failure."""
    import subprocess

    with tempfile.NamedTemporaryFile(mode="w", suffix=".tsv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["tesseract", str(frame_path), tmp_path.replace(".tsv", ""), "tsv"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("Tesseract failed for %s: %s", frame_path.name, result.stderr)
            return None

        tsv_path = Path(tmp_path.replace(".tsv", ".tsv"))
        if not tsv_path.exists():
            tsv_path = Path(tmp_path)
        if not tsv_path.exists():
            return None

        return tsv_path.read_text().strip().split("\n")
    finally:
        for ext in (".tsv", ".txt"):
            cleanup_path = Path(tmp_path.replace(".tsv", ext))
            if cleanup_path.exists():
                cleanup_path.unlink()


def run_ocr_on_frame(frame_path: Path, min_confidence: float = 60.0) -> FrameOCRResult | None:
    """Run Tesseract OCR on a single frame image.

    Returns None if tesseract is not available or OCR produces no text.
    """
    if not _check_tesseract():
        logger.warning("Tesseract not available, skipping OCR for %s", frame_path.name)
        return None

    timestamp = _timestamp_from_filename(frame_path)
    lines = _run_tesseract(frame_path)
    if lines is None:
        return None

    words, confidences = _parse_tsv_words(lines, min_confidence)
    if not words:
        return None

    avg_confidence = sum(confidences) / len(confidences)
    return FrameOCRResult(
        frame_path=str(frame_path),
        timestamp=timestamp,
        text=" ".join(words),
        confidence=avg_confidence,
        word_count=len(words),
    )


def run_ocr_on_directory(
    frames_dir: Path,
    min_confidence: float = 60.0,
) -> tuple[FrameOCRResult, ...]:
    """Run OCR on all PNG frames in a directory."""
    if not frames_dir.is_dir():
        raise FileNotFoundError(f"Frames directory not found: {frames_dir}")

    frames = sorted(frames_dir.glob("*.png"))
    if not frames:
        logger.warning("No PNG frames found in %s", frames_dir)
        return ()

    results: list[FrameOCRResult] = []
    for frame in frames:
        result = run_ocr_on_frame(frame, min_confidence)
        if result is not None:
            results.append(result)

    return tuple(results)


def write_results(results: tuple[FrameOCRResult, ...], output_path: Path) -> None:
    """Write OCR results to JSON file using atomic write."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=output_path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(
                {
                    "frames_analyzed": len(results),
                    "frames_with_text": sum(1 for r in results if r.word_count > 0),
                    "results": [asdict(r) for r in results],
                },
                f,
                indent=2,
            )
        os.replace(tmp_path, output_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="OCR screen share frames using Tesseract")
    parser.add_argument("frames_dir", type=Path, help="Directory containing PNG frames")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON path")
    parser.add_argument("--confidence", type=float, default=60.0, help="Minimum OCR confidence (0-100)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not _check_tesseract():
        logger.error("Tesseract is not installed. Install with: apt install tesseract-ocr")
        sys.exit(1)

    results = run_ocr_on_directory(args.frames_dir, args.confidence)
    write_results(results, args.output)
    text_count = sum(1 for r in results if r.word_count > 0)
    logger.info("OCR complete: %d frames analyzed, %d with text", len(results), text_count)


if __name__ == "__main__":
    main()
