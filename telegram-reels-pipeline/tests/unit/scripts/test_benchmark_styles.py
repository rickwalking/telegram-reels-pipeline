"""Tests for scripts/benchmark_styles.py — benchmark logic with mocked subprocess."""

from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts"))
import benchmark_styles


class TestStyleFilters:
    def test_all_styles_have_filters(self) -> None:
        for style in benchmark_styles.ALL_STYLES:
            assert style in benchmark_styles.STYLE_FILTERS

    def test_default_is_fast_tier(self) -> None:
        assert benchmark_styles.STYLE_FILTERS["default"]["tier"] == "fast"

    def test_split_horizontal_is_premium_tier(self) -> None:
        assert benchmark_styles.STYLE_FILTERS["split_horizontal"]["tier"] == "premium"

    def test_pip_is_premium_tier(self) -> None:
        assert benchmark_styles.STYLE_FILTERS["pip"]["tier"] == "premium"

    def test_all_filters_have_setsar(self) -> None:
        for style, info in benchmark_styles.STYLE_FILTERS.items():
            assert "setsar=1" in info["filter"], f"{style} filter missing setsar=1"


class TestBenchmarkResult:
    def test_frozen(self) -> None:
        result = benchmark_styles.BenchmarkResult(
            style="default",
            tier="fast",
            peak_rss_mb=100.0,
            wall_clock_seconds=5.0,
            encode_ratio=1.0,
            verdict="FULL_PASS",
        )
        with pytest.raises(AttributeError):
            result.verdict = "FAIL"  # type: ignore[misc]

    def test_asdict(self) -> None:
        result = benchmark_styles.BenchmarkResult(
            style="pip",
            tier="premium",
            peak_rss_mb=512.0,
            wall_clock_seconds=10.0,
            encode_ratio=2.0,
            verdict="FULL_PASS",
        )
        d = asdict(result)
        assert d["style"] == "pip"
        assert d["tier"] == "premium"
        assert d["verdict"] == "FULL_PASS"


class TestRunStyleBenchmark:
    def test_unknown_style_returns_fail(self, tmp_path: Path) -> None:
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)
        result = benchmark_styles.run_style_benchmark(video, "nonexistent")
        assert result.verdict == "FAIL"
        assert result.tier == "unknown"

    def test_successful_encode(self, tmp_path: Path) -> None:
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)

        def _fake_run(cmd, **kwargs):
            # Create the output file to simulate successful encoding
            for i, arg in enumerate(cmd):
                if isinstance(arg, str) and arg.endswith(".mp4") and i == len(cmd) - 1:
                    Path(arg).write_bytes(b"\x00" * 1000)
            return MagicMock(returncode=0)

        with patch("benchmark_styles.subprocess.run", side_effect=_fake_run):
            result = benchmark_styles.run_style_benchmark(video, "default", duration=1.0)

        assert result.style == "default"
        assert result.tier == "fast"
        assert result.wall_clock_seconds >= 0
        assert result.verdict in ("FULL_PASS", "PARTIAL_PASS")

    def test_timeout_returns_fail(self, tmp_path: Path) -> None:
        import subprocess

        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)

        with patch("benchmark_styles.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 60)):
            result = benchmark_styles.run_style_benchmark(video, "default", duration=1.0)

        assert result.verdict == "FAIL"


class TestRunAllBenchmarks:
    def test_runs_all_styles(self, tmp_path: Path) -> None:
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)

        fake_result = benchmark_styles.BenchmarkResult(
            style="x",
            tier="fast",
            peak_rss_mb=100.0,
            wall_clock_seconds=1.0,
            encode_ratio=0.2,
            verdict="FULL_PASS",
        )

        with patch.object(benchmark_styles, "run_style_benchmark", return_value=fake_result):
            report = benchmark_styles.run_all_benchmarks(video)

        assert len(report.results) == len(benchmark_styles.ALL_STYLES)
        assert report.source_video == str(video)

    def test_single_style_filter(self, tmp_path: Path) -> None:
        video = tmp_path / "test.mp4"
        video.write_bytes(b"\x00" * 100)

        fake_result = benchmark_styles.BenchmarkResult(
            style="pip",
            tier="premium",
            peak_rss_mb=200.0,
            wall_clock_seconds=3.0,
            encode_ratio=0.6,
            verdict="FULL_PASS",
        )

        with patch.object(benchmark_styles, "run_style_benchmark", return_value=fake_result):
            report = benchmark_styles.run_all_benchmarks(video, styles=("pip",))

        assert len(report.results) == 1
        assert report.results[0]["style"] == "pip"


class TestGetPeakRssMb:
    def test_returns_float(self) -> None:
        result = benchmark_styles._get_peak_rss_mb()
        assert isinstance(result, float)

    def test_handles_missing_proc(self) -> None:
        with patch("builtins.open", side_effect=OSError("no /proc")):
            result = benchmark_styles._get_peak_rss_mb()
        assert result == 0.0


class TestThresholds:
    def test_max_rss_reasonable(self) -> None:
        assert benchmark_styles.MAX_RSS_MB <= 3072  # Must stay under 3GB

    def test_benchmark_duration_short(self) -> None:
        assert benchmark_styles.BENCHMARK_DURATION_SECONDS <= 10.0
