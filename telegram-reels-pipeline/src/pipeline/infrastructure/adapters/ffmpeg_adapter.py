"""FFmpegAdapter — VideoProcessingPort implementation using FFmpeg subprocess."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
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
                    "-ss",
                    str(ts),
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
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
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
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

    async def execute_encoding_plan(self, plan_path: Path, workspace: Path | None = None) -> list[Path]:
        """Execute all commands from an encoding-plan.json produced by the FFmpeg Engineer agent.

        Reads the plan, builds and runs each FFmpeg command using the encoding
        parameters from encoding-params.md (H.264 Main, CRF 23, medium preset,
        yuv420p, AAC 128k, faststart). Supports both simple crop filters and
        filter_complex graphs (for split-screen/PiP).

        Args:
            plan_path: Path to encoding-plan.json.
            workspace: Workspace root for path confinement. Defaults to plan_path's parent.
                       All input/output paths in the plan must resolve within this directory.

        Returns list of produced segment file paths.
        Raises FFmpegError if the plan is missing/invalid or a command fails.
        """
        commands = self._load_plan_commands(plan_path)
        ws_root = (workspace or plan_path.parent).resolve()

        produced: list[Path] = []
        for i, cmd in enumerate(commands):
            output_path = self._execute_plan_command(cmd, i, ws_root)
            produced.append(await self._encode_plan_segment(cmd, i, output_path, len(commands), ws_root))

        logger.info("Executed encoding plan: %d segments produced", len(produced))
        return produced

    @staticmethod
    def _load_plan_commands(plan_path: Path) -> list[dict[str, object]]:
        """Load and validate encoding-plan.json, returning the commands list."""
        if not plan_path.exists():
            raise FFmpegError(f"Encoding plan not found: {plan_path}")

        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise FFmpegError(f"Invalid encoding plan JSON: {exc}") from exc

        if not isinstance(plan, dict):
            raise FFmpegError(f"Encoding plan root must be an object, got {type(plan).__name__}")

        commands: list[dict[str, object]] = plan.get("commands", [])
        if not commands:
            raise FFmpegError("Encoding plan has no commands")
        return commands

    def _execute_plan_command(
        self,
        cmd: dict[str, object],
        index: int,
        ws_root: Path,
    ) -> Path:
        """Validate a single plan command and return the resolved output path."""
        try:
            output_str = cmd["output"]
            input_str = cmd["input"]
            _ = cmd["start_seconds"]
            _ = cmd["end_seconds"]
        except KeyError as exc:
            raise FFmpegError(f"Command {index + 1} missing required field: {exc}") from exc

        # Resolve relative paths against workspace (not CWD).
        # Absolute paths pass through unchanged (Path("/ws") / "/abs" == "/abs").
        output_path = (ws_root / str(output_str)).resolve()
        input_path = (ws_root / str(input_str)).resolve()
        self._validate_path_confinement(input_path, ws_root, "input", index + 1)
        self._validate_path_confinement(output_path, ws_root, "output", index + 1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    async def _encode_plan_segment(
        self,
        cmd: dict[str, object],
        index: int,
        output_path: Path,
        total: int,
        ws_root: Path,
    ) -> Path:
        """Build ffmpeg args for one plan command, encode to tmp, and atomically rename."""
        input_path = (ws_root / str(cmd["input"])).resolve()
        start = cmd["start_seconds"]
        end = cmd["end_seconds"]

        args: list[str] = ["-ss", str(start), "-to", str(end), "-i", str(input_path)]

        filter_type = cmd.get("filter_type", "crop")
        if filter_type == "filter_complex" and cmd.get("filter_complex"):
            args.extend(["-filter_complex", str(cmd["filter_complex"])])
            args.extend(["-map", "[v]", "-map", "0:a?"])
        else:
            crop_filter = cmd.get("crop_filter")
            if not crop_filter:
                raise FFmpegError(f"Command {index + 1} missing crop_filter")
            args.extend(["-vf", str(crop_filter)])

        fd, tmp_path_str = tempfile.mkstemp(dir=str(output_path.parent), suffix=".tmp.mp4")
        os.close(fd)
        tmp_path = Path(tmp_path_str)

        args.extend(
            [
                "-c:v",
                "libx264",
                "-profile:v",
                "main",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-movflags",
                "+faststart",
                "-threads",
                str(self._threads),
                "-y",
                str(tmp_path),
            ]
        )

        logger.info("Encoding segment %d/%d: %s", index + 1, total, output_path.name)
        try:
            await self._run_ffmpeg(*args)

            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise FFmpegError(f"FFmpeg produced no output for segment {index + 1}: {output_path}")

            os.replace(str(tmp_path), str(output_path))
        except BaseException:
            tmp_path.unlink(missing_ok=True)
            raise

        return output_path

    @staticmethod
    def _validate_path_confinement(
        path: Path,
        workspace: Path,
        label: str,
        cmd_index: int,
    ) -> None:
        """Ensure a resolved path is within the workspace. Rejects symlink escapes."""
        try:
            path.relative_to(workspace)
        except ValueError:
            raise FFmpegError(f"Command {cmd_index} {label} path escapes workspace: {path}") from None

    async def _encode_segment(self, video: Path, segment: SegmentLayout, output: Path) -> None:
        """Encode a single segment with crop and scale to 1080x1920."""
        crop = segment.crop_region
        if crop is None:
            raise FFmpegError(f"crop_region is None for segment '{segment.layout_name}'")

        vf = f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y},scale=1080:1920"
        await self._run_ffmpeg(
            "-i",
            str(video),
            "-ss",
            str(segment.start_seconds),
            "-to",
            str(segment.end_seconds),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-threads",
            str(self._threads),
            "-y",
            str(output),
        )

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg concat demuxer (single quotes -> '\\'')."""
        escaped = str(path.resolve()).replace("'", "'\\''")
        return f"file '{escaped}'"

    async def _concat_files(self, files: list[Path], output: Path) -> None:
        """Concatenate files using FFmpeg concat demuxer."""
        list_file = output.parent / f"_concat_{output.stem}.txt"
        list_file.write_text("\n".join(self._escape_concat_path(f) for f in files))
        try:
            await self._run_ffmpeg(
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-y",
                str(output),
            )
        finally:
            list_file.unlink(missing_ok=True)

    async def _run_ffmpeg(self, *args: str) -> str:
        """Run an FFmpeg command and return stdout."""
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise FFmpegError(f"FFmpeg failed (exit {proc.returncode}): {stderr.decode()}")
        return stdout.decode()
