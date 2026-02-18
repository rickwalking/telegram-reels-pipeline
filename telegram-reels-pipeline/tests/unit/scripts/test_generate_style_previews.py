"""Tests for generate_style_previews — style preview clip generation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.generate_style_previews import (
    STYLE_PREVIEWS,
    PreviewResult,
    generate_preview,
    resolve_filter,
    write_manifest,
)


class TestPreviewResult:
    def test_frozen(self) -> None:
        r = PreviewResult(style="default", label="Default", output_path="p.mp4", success=True)
        with pytest.raises(AttributeError):
            r.success = False  # type: ignore[misc]

    def test_error_default_none(self) -> None:
        r = PreviewResult(style="default", label="Default", output_path="p.mp4", success=True)
        assert r.error is None

    def test_error_field(self) -> None:
        r = PreviewResult(style="pip", label="PiP", output_path="p.mp4", success=False, error="fail")
        assert r.error == "fail"


class TestResolveFilter:
    def test_vf_filter(self) -> None:
        style_def = {"filter": "crop=608:1080:{x_left}:0,scale=1080:1920:flags=lanczos,setsar=1"}
        ft, fstr = resolve_filter(style_def, x_left=300, x_right=1200)
        assert ft == "vf"
        assert "300" in fstr
        assert "{x_left}" not in fstr

    def test_filter_complex(self) -> None:
        style_def = {"filter_complex": "[top]crop=960:1080:{x_left}:0;[bot]crop=960:1080:{x_right}:0"}
        ft, fstr = resolve_filter(style_def, x_left=100, x_right=900)
        assert ft == "filter_complex"
        assert "100" in fstr
        assert "900" in fstr


class TestStylePreviewsDefinitions:
    def test_all_styles_defined(self) -> None:
        assert "default" in STYLE_PREVIEWS
        assert "split_horizontal" in STYLE_PREVIEWS
        assert "pip" in STYLE_PREVIEWS

    def test_each_style_has_label(self) -> None:
        for name, defn in STYLE_PREVIEWS.items():
            assert "label" in defn, f"{name} missing label"

    def test_filter_complex_styles_end_with_v_label(self) -> None:
        for name, defn in STYLE_PREVIEWS.items():
            if "filter_complex" in defn:
                assert defn["filter_complex"].endswith("[v]"), f"{name} filter_complex must end with [v] for -map [v]"


def _mock_process(returncode: int = 0, stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", stderr))
    proc.returncode = returncode
    return proc


class TestGeneratePreview:
    async def test_successful_preview(self, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        source.write_bytes(b"video")

        with patch("scripts.generate_style_previews.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(return_value=_mock_process())
            mock_aio.subprocess = __import__("asyncio").subprocess
            result = await generate_preview(
                source,
                "default",
                STYLE_PREVIEWS["default"],
                60.0,
                300,
                1200,
                tmp_path,
            )

        assert result.success is True
        assert result.style == "default"

    async def test_failed_preview(self, tmp_path: Path) -> None:
        source = tmp_path / "source.mp4"
        source.write_bytes(b"video")

        with patch("scripts.generate_style_previews.asyncio") as mock_aio:
            mock_aio.create_subprocess_exec = AsyncMock(
                return_value=_mock_process(returncode=1, stderr=b"encoding error"),
            )
            mock_aio.subprocess = __import__("asyncio").subprocess
            result = await generate_preview(
                source,
                "pip",
                STYLE_PREVIEWS["pip"],
                60.0,
                300,
                1200,
                tmp_path,
            )

        assert result.success is False
        assert result.error is not None


class TestWriteManifest:
    def test_writes_json(self, tmp_path: Path) -> None:
        results = (PreviewResult(style="default", label="Default", output_path="p.mp4", success=True),)
        manifest = write_manifest(results, tmp_path)
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["successful"] == 1
        assert data["total"] == 1

    def test_atomic_write(self, tmp_path: Path) -> None:
        write_manifest((), tmp_path)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
        assert json_files[0].name == "preview-manifest.json"
