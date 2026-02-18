"""Generate 5-second preview clips for each framing style.

Extracts a representative 5-second segment from a source video and applies
each style's filter chain to produce preview clips for user comparison.

Usage::

    poetry run python scripts/generate_style_previews.py <source_video> \\
        --start 60.0 --faces-left 300 --faces-right 1200 \\
        --output-dir <workspace>/previews
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Preview duration in seconds
_PREVIEW_DURATION: float = 5.0

# Style filter definitions — each style maps to an FFmpeg filter string.
# Placeholders: {x_left}, {x_right} are resolved from face positions.
STYLE_PREVIEWS: dict[str, dict[str, str]] = {
    "default": {
        "label": "Default (single crop)",
        "filter": "crop=608:1080:{x_left}:0,scale=1080:1920:flags=lanczos,setsar=1",
    },
    "split_horizontal": {
        "label": "Split Screen",
        "filter_complex": (
            "split=2[top][bot];"
            "[top]crop=960:1080:{x_left}:0,scale=1080:960:flags=lanczos[t];"
            "[bot]crop=960:1080:{x_right}:0,scale=1080:960:flags=lanczos[b];"
            "[t][b]vstack,setsar=1"
        ),
    },
    "pip": {
        "label": "Picture-in-Picture",
        "filter_complex": (
            "split=2[main][pip];"
            "[main]crop=608:1080:{x_left}:0,scale=1080:1920:flags=lanczos[m];"
            "[pip]crop=608:1080:{x_right}:0,scale=280:500:flags=lanczos[p];"
            "[m][p]overlay=760:1380,setsar=1"
        ),
    },
}


@dataclass(frozen=True)
class PreviewResult:
    """Result of generating a style preview clip."""

    style: str
    label: str
    output_path: str
    success: bool
    error: str | None = None


def resolve_filter(
    style_def: dict[str, str],
    x_left: int,
    x_right: int,
) -> tuple[str, str]:
    """Resolve a style filter definition with face positions.

    Returns (filter_type, filter_string) where filter_type is "vf" or "filter_complex".
    """
    if "filter_complex" in style_def:
        resolved = style_def["filter_complex"].format(x_left=x_left, x_right=x_right)
        return "filter_complex", resolved
    resolved = style_def["filter"].format(x_left=x_left, x_right=x_right)
    return "vf", resolved


async def generate_preview(
    source: Path,
    style_name: str,
    style_def: dict[str, str],
    start_seconds: float,
    x_left: int,
    x_right: int,
    output_dir: Path,
) -> PreviewResult:
    """Generate a single 5-second preview clip for a given style."""
    output_path = output_dir / f"preview-{style_name}.mp4"
    label = style_def.get("label", style_name)

    filter_type, filter_str = resolve_filter(style_def, x_left, x_right)

    cmd = [
        "ffmpeg",
        "-ss",
        str(start_seconds),
        "-i",
        str(source),
        "-t",
        str(_PREVIEW_DURATION),
    ]

    if filter_type == "filter_complex":
        cmd.extend(["-filter_complex", filter_str, "-map", "[v]"])
    else:
        cmd.extend(["-vf", filter_str])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-preset",
            "fast",
            "-an",
            "-y",
            str(output_path),
        ]
    )

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode()[:500]
        logger.warning("Preview %s failed: %s", style_name, error_msg)
        return PreviewResult(
            style=style_name,
            label=label,
            output_path=str(output_path),
            success=False,
            error=error_msg,
        )

    return PreviewResult(
        style=style_name,
        label=label,
        output_path=str(output_path),
        success=True,
    )


async def generate_all_previews(
    source: Path,
    start_seconds: float,
    x_left: int,
    x_right: int,
    output_dir: Path,
) -> tuple[PreviewResult, ...]:
    """Generate preview clips for all styles."""
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[PreviewResult] = []
    for style_name, style_def in STYLE_PREVIEWS.items():
        result = await generate_preview(
            source,
            style_name,
            style_def,
            start_seconds,
            x_left,
            x_right,
            output_dir,
        )
        results.append(result)

    return tuple(results)


def write_manifest(results: tuple[PreviewResult, ...], output_dir: Path) -> Path:
    """Write preview manifest JSON using atomic write."""
    manifest_path = output_dir / "preview-manifest.json"
    fd, tmp_path = tempfile.mkstemp(dir=output_dir, suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(
                {
                    "previews": [asdict(r) for r in results],
                    "successful": sum(1 for r in results if r.success),
                    "total": len(results),
                },
                f,
                indent=2,
            )
        os.replace(tmp_path, manifest_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return manifest_path


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate style preview clips")
    parser.add_argument("source", type=Path, help="Source video path")
    parser.add_argument("--start", type=float, default=60.0, help="Start timestamp")
    parser.add_argument("--faces-left", type=int, default=300, help="Left speaker face X")
    parser.add_argument("--faces-right", type=int, default=1200, help="Right speaker face X")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not args.source.exists():
        logger.error("Source video not found: %s", args.source)
        raise SystemExit(1)

    results = asyncio.run(
        generate_all_previews(
            args.source,
            args.start,
            args.faces_left,
            args.faces_right,
            args.output_dir,
        )
    )
    manifest = write_manifest(results, args.output_dir)
    ok = sum(1 for r in results if r.success)
    logger.info("Generated %d/%d previews. Manifest: %s", ok, len(results), manifest)


if __name__ == "__main__":
    main()
