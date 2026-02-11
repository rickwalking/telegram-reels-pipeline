"""FFmpegAdapter — VideoProcessingPort implementation using FFmpeg subprocess."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.domain.errors import PipelineError

if TYPE_CHECKING:
    from pipeline.domain.models import SegmentLayout

logger = logging.getLogger(__name__)

# Default thread count for FFmpeg on Raspberry Pi
_DEFAULT_THREADS: int = 2


class FFmpegError(PipelineError):
    """FFmpeg subprocess failed."""


class FFmpegAdapter:
    """Video processing via FFmpeg — frame extraction, crop, and encode.

    Implements VideoProcessingPort for the pipeline infrastructure layer.
    """

    def __init__(self, threads: int = _DEFAULT_THREADS) -> None:
        self._threads = threads

    async def extract_frames(self, video: Path, timestamps: list[float]) -> list[Path]:
        """Extract JPEG frames at specified timestamps.

        Returns list of frame file paths in the same directory as the video.
        """
        if not video.exists():
            raise FFmpegError(f"Video file not found: {video}")

        frames: list[Path] = []
        for ts in timestamps:
            output = video.parent / f"frame_{ts:.3f}.jpg"
            try:
                await self._run_ffmpeg(
                    "-ss", str(ts),
                    "-i", str(video),
                    "-frames:v", "1",
                    "-q:v", "2",
                    "-y",
                    str(output),
                )
            except FFmpegError as exc:
                raise FFmpegError(f"Failed to extract frame at {ts}s: {exc}") from exc
            frames.append(output)

        logger.info("Extracted %d frames from %s", len(frames), video.name)
        return frames

    async def crop_and_encode(self, video: Path, segments: list[SegmentLayout], output: Path) -> Path:
        """Crop and encode video segments to vertical 9:16 (1080x1920).

        Each segment must have a non-None crop_region. Multiple segments
        are encoded separately then concatenated via FFmpeg concat demuxer.
        """
        if not segments:
            raise FFmpegError("segments must not be empty")
        if not video.exists():
            raise FFmpegError(f"Video file not found: {video}")

        output.parent.mkdir(parents=True, exist_ok=True)
        for seg in segments:
            if seg.crop_region is None:
                raise FFmpegError(f"crop_region required for segment '{seg.layout_name}'")

        if len(segments) == 1:
            await self._encode_segment(video, segments[0], output)
            return output

        # Multiple segments: encode each, then concat
        temp_files: list[Path] = []
        try:
            for i, seg in enumerate(segments):
                temp_out = output.parent / f"_seg_{i:03d}{output.suffix}"
                await self._encode_segment(video, seg, temp_out)
                temp_files.append(temp_out)

            await self._concat_files(temp_files, output)
        finally:
            for f in temp_files:
                f.unlink(missing_ok=True)

        logger.info("Encoded %d segments into %s", len(segments), output.name)
        return output

    async def concat_videos(self, videos: list[Path], output: Path) -> Path:
        """Concatenate multiple video files into a single output using stream copy."""
        if not videos:
            raise FFmpegError("videos must not be empty")
        output.parent.mkdir(parents=True, exist_ok=True)
        if len(videos) == 1:
            import shutil

            shutil.copy2(videos[0], output)
            return output

        await self._concat_files(videos, output)
        logger.info("Concatenated %d videos into %s", len(videos), output.name)
        return output

    async def probe_duration(self, video: Path) -> float:
        """Get video duration in seconds using ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise FFmpegError(f"ffprobe failed: {stderr.decode()}")

        try:
            return float(stdout.decode().strip())
        except ValueError as exc:
            raise FFmpegError(f"Could not parse duration: {stdout.decode()}") from exc

    async def _encode_segment(self, video: Path, segment: SegmentLayout, output: Path) -> None:
        """Encode a single segment with crop and scale to 1080x1920."""
        crop = segment.crop_region
        if crop is None:
            raise FFmpegError(f"crop_region is None for segment '{segment.layout_name}'")

        vf = f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y},scale=1080:1920"
        await self._run_ffmpeg(
            "-i", str(video),
            "-ss", str(segment.start_seconds),
            "-to", str(segment.end_seconds),
            "-vf", vf,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-threads", str(self._threads),
            "-y",
            str(output),
        )

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg concat demuxer (single quotes -> '\\''). """
        escaped = str(path.resolve()).replace("'", "'\\''")
        return f"file '{escaped}'"

    async def _concat_files(self, files: list[Path], output: Path) -> None:
        """Concatenate files using FFmpeg concat demuxer."""
        list_file = output.parent / f"_concat_{output.stem}.txt"
        list_file.write_text(
            "\n".join(self._escape_concat_path(f) for f in files)
        )
        try:
            await self._run_ffmpeg(
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                "-y",
                str(output),
            )
        finally:
            list_file.unlink(missing_ok=True)

    async def _run_ffmpeg(self, *args: str) -> str:
        """Run an FFmpeg command and return stdout."""
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise FFmpegError(f"FFmpeg failed (exit {proc.returncode}): {stderr.decode()}")
        return stdout.decode()
