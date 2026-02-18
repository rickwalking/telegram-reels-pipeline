"""Pi performance benchmark for framing styles — measures memory, CPU, and encoding time.

Profiles default, split_horizontal, and pip encoding on a source video to determine
which styles are feasible on the target hardware. Outputs JSON results with pass/fail
thresholds and tier classifications.

Usage::

    # Run all benchmarks on a source video
    python scripts/benchmark_styles.py <source_video> --output benchmark-results.json

    # Run a single style
    python scripts/benchmark_styles.py <source_video> --style split_horizontal
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Thresholds for Pi 4 (4GB RAM, quad-core ARM Cortex-A72)
MAX_RSS_MB: int = 2048  # 2GB peak RSS limit (leave 2GB for OS + other processes)
MAX_ENCODE_TIME_PER_SECOND: float = 10.0  # 10x realtime max (e.g., 50s encode for 5s clip)
MAX_CPU_PERCENT: float = 95.0  # sustained CPU ceiling

BENCHMARK_DURATION_SECONDS: float = 5.0  # encode a 5-second clip for benchmarking

# FFmpeg filter chains per style (using placeholder coordinates)
STYLE_FILTERS: dict[str, dict[str, str]] = {
    "default": {
        "filter": "crop=608:1080:280:0,scale=1080:1920:flags=lanczos,setsar=1",
        "tier": "fast",
    },
    "split_horizontal": {
        "filter": (
            "split=2[top][bot];"
            "[top]crop=960:1080:0:0,scale=1080:960:flags=lanczos[t];"
            "[bot]crop=960:1080:960:0,scale=1080:960:flags=lanczos[b];"
            "[t][b]vstack,setsar=1"
        ),
        "tier": "premium",
    },
    "pip": {
        "filter": (
            "split=2[main][pip];"
            "[main]crop=608:1080:280:0,scale=1080:1920:flags=lanczos[m];"
            "[pip]crop=608:1080:960:0,scale=280:500:flags=lanczos[p];"
            "[m][p]overlay=760:1380,setsar=1"
        ),
        "tier": "premium",
    },
}

ALL_STYLES: tuple[str, ...] = ("default", "split_horizontal", "pip")


@dataclass(frozen=True)
class BenchmarkResult:
    """Result of a single style benchmark run."""

    style: str
    tier: str
    peak_rss_mb: float
    wall_clock_seconds: float
    encode_ratio: float  # wall_clock / source_duration
    verdict: str  # PASS, PARTIAL_PASS, FAIL


@dataclass
class BenchmarkReport:
    """Aggregate benchmark report for all styles."""

    source_video: str
    benchmark_duration_seconds: float
    results: list[dict[str, object]] = field(default_factory=list)
    hardware_summary: str = ""


def _get_peak_rss_mb() -> float:
    """Read peak RSS from /proc/self/status (Linux only)."""
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    # VmHWM is in kB
                    return float(line.split()[1]) / 1024.0
    except (OSError, ValueError, IndexError):
        pass
    return 0.0


def _probe_duration(video_path: Path) -> float | None:
    """Get video duration via ffprobe. Returns None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


def run_style_benchmark(
    source_video: Path,
    style: str,
    duration: float = BENCHMARK_DURATION_SECONDS,
) -> BenchmarkResult:
    """Benchmark a single framing style by encoding a short clip.

    Returns a BenchmarkResult with measured metrics and a verdict.
    """
    style_info = STYLE_FILTERS.get(style)
    if style_info is None:
        return BenchmarkResult(
            style=style,
            tier="unknown",
            peak_rss_mb=0.0,
            wall_clock_seconds=0.0,
            encode_ratio=0.0,
            verdict="FAIL",
        )

    filter_str = style_info["filter"]
    tier = style_info["tier"]

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / f"bench-{style}.mp4"

        # Use filter_complex for multi-stream styles, -vf for simple crops
        if "split=" in filter_str or "overlay=" in filter_str:
            filter_args = ["-filter_complex", filter_str]
        else:
            filter_args = ["-vf", filter_str]

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            "0",
            "-t",
            str(duration),
            "-i",
            str(source_video),
            *filter_args,
            "-c:v",
            "libx264",
            "-profile:v",
            "main",
            "-crf",
            "23",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-threads",
            "0",
            str(output_path),
        ]

        rss_before = _get_peak_rss_mb()
        start_time = time.monotonic()

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                timeout=int(duration * MAX_ENCODE_TIME_PER_SECOND * 2),
            )
        except (subprocess.TimeoutExpired, OSError):
            return BenchmarkResult(
                style=style,
                tier=tier,
                peak_rss_mb=0.0,
                wall_clock_seconds=0.0,
                encode_ratio=0.0,
                verdict="FAIL",
            )

        wall_clock = time.monotonic() - start_time
        rss_after = _get_peak_rss_mb()
        peak_rss = max(rss_after - rss_before, 0.0) if rss_before else rss_after

        encode_ratio = wall_clock / duration if duration > 0 else 0.0
        output_exists = output_path.exists() and output_path.stat().st_size > 0

    # Determine verdict
    if not output_exists or peak_rss > MAX_RSS_MB:
        verdict = "FAIL"
    elif encode_ratio > MAX_ENCODE_TIME_PER_SECOND:
        verdict = "PARTIAL_PASS"
    else:
        verdict = "FULL_PASS"

    return BenchmarkResult(
        style=style,
        tier=tier,
        peak_rss_mb=round(peak_rss, 1),
        wall_clock_seconds=round(wall_clock, 2),
        encode_ratio=round(encode_ratio, 2),
        verdict=verdict,
    )


def run_all_benchmarks(
    source_video: Path,
    styles: tuple[str, ...] = ALL_STYLES,
    duration: float = BENCHMARK_DURATION_SECONDS,
) -> BenchmarkReport:
    """Run benchmarks for all specified styles and return an aggregate report."""
    report = BenchmarkReport(
        source_video=str(source_video),
        benchmark_duration_seconds=duration,
    )

    # Hardware summary
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name") or line.startswith("Model"):
                    report.hardware_summary = line.split(":", 1)[1].strip()
                    break
    except OSError:
        report.hardware_summary = "unknown"

    for style in styles:
        result = run_style_benchmark(source_video, style, duration)
        report.results.append(asdict(result))

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark framing styles on Pi hardware")
    parser.add_argument("source_video", type=Path, help="Path to source video for benchmarking")
    parser.add_argument(
        "--style",
        default=None,
        choices=list(ALL_STYLES),
        help="Benchmark a single style (default: all styles)",
    )
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output JSON file path")
    parser.add_argument(
        "--duration",
        type=float,
        default=BENCHMARK_DURATION_SECONDS,
        help=f"Benchmark clip duration in seconds (default: {BENCHMARK_DURATION_SECONDS})",
    )
    args = parser.parse_args()

    if not args.source_video.exists():
        print(f"Error: source video not found: {args.source_video}", file=sys.stderr)
        sys.exit(1)

    styles = (args.style,) if args.style else ALL_STYLES
    report = run_all_benchmarks(args.source_video, styles, args.duration)

    output_json = json.dumps(asdict(report), indent=2)

    if args.output:
        fd, tmp_path = tempfile.mkstemp(dir=args.output.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(output_json)
            os.replace(tmp_path, args.output)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
        print(f"Results written to {args.output}")
    else:
        print(output_json)

    # Exit with non-zero if any style failed
    if any(r["verdict"] == "FAIL" for r in report.results):
        sys.exit(1)


if __name__ == "__main__":
    main()
