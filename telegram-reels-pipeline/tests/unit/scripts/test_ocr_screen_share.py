"""Tests for ocr_screen_share — Tesseract OCR on screen share frames."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Import must work even without tesseract installed
from scripts.ocr_screen_share import (
    FrameOCRResult,
    _timestamp_from_filename,
    run_ocr_on_directory,
    write_results,
)


class TestFrameOCRResult:
    def test_frozen(self) -> None:
        r = FrameOCRResult(frame_path="f.png", timestamp=10.0, text="hello", confidence=90.0, word_count=1)
        with pytest.raises(AttributeError):
            r.text = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        r = FrameOCRResult(frame_path="f.png", timestamp=5.0, text="hello world", confidence=85.0, word_count=2)
        assert r.word_count == 2
        assert r.confidence == 85.0


class TestTimestampFromFilename:
    def test_standard_frame_name(self) -> None:
        assert _timestamp_from_filename(Path("frame_1260.png")) == 1260.0

    def test_fractional_timestamp(self) -> None:
        assert _timestamp_from_filename(Path("frame_1260.5.png")) == 1260.5

    def test_non_standard_name(self) -> None:
        assert _timestamp_from_filename(Path("unknown.png")) == 0.0

    def test_frame_prefix_only(self) -> None:
        assert _timestamp_from_filename(Path("frame_0.png")) == 0.0


class TestRunOcrOnDirectory:
    def test_missing_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            run_ocr_on_directory(tmp_path / "nonexistent")

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        result = run_ocr_on_directory(tmp_path)
        assert result == ()

    @patch("scripts.ocr_screen_share._check_tesseract", return_value=False)
    def test_no_tesseract_returns_empty(self, _mock_check: object, tmp_path: Path) -> None:
        # Create a dummy frame
        (tmp_path / "frame_10.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        result = run_ocr_on_directory(tmp_path)
        assert result == ()


class TestWriteResults:
    def test_writes_json(self, tmp_path: Path) -> None:
        results = (FrameOCRResult(frame_path="f.png", timestamp=10.0, text="hello", confidence=90.0, word_count=1),)
        output = tmp_path / "ocr.json"
        write_results(results, output)
        assert output.exists()

        import json

        data = json.loads(output.read_text())
        assert data["frames_analyzed"] == 1
        assert data["frames_with_text"] == 1
        assert data["results"][0]["text"] == "hello"

    def test_atomic_write(self, tmp_path: Path) -> None:
        output = tmp_path / "ocr.json"
        write_results((), output)
        assert output.exists()
        # No temp files should remain
        assert len(list(tmp_path.glob("*.json"))) == 1

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        output = tmp_path / "deep" / "nested" / "ocr.json"
        write_results((), output)
        assert output.exists()
