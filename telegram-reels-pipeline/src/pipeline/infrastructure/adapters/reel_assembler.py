"""Reel assembler — concatenate encoded video segments into a final reel."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from pipeline.domain.enums import TransitionKind
from pipeline.domain.errors import PipelineError
from pipeline.domain.models import BrollPlacement

logger = logging.getLogger(__name__)

# Default xfade transition durations in seconds
_STYLE_CHANGE_DURATION: float = 0.5
_NARRATIVE_BOUNDARY_DURATION: float = 1.0

# Default effect for narrative boundary transitions
_NARRATIVE_BOUNDARY_EFFECT: str = "dissolve"


@dataclass(frozen=True)
class TransitionSpec:
    """Specification for a transition between two segments."""

    offset_seconds: float
    effect: str = "fade"
    duration: float = _STYLE_CHANGE_DURATION
    kind: TransitionKind = TransitionKind.STYLE_CHANGE


def make_transition(
    offset_seconds: float,
    kind: TransitionKind = TransitionKind.STYLE_CHANGE,
    effect: str | None = None,
) -> TransitionSpec:
    """Create a TransitionSpec with sensible defaults based on kind.

    Narrative boundaries get dissolve (1.0s). Style changes get slide/wipe (0.5s).
    """
    if kind == TransitionKind.NARRATIVE_BOUNDARY:
        return TransitionSpec(
            offset_seconds=offset_seconds,
            effect=effect or _NARRATIVE_BOUNDARY_EFFECT,
            duration=_NARRATIVE_BOUNDARY_DURATION,
            kind=kind,
        )
    return TransitionSpec(
        offset_seconds=offset_seconds,
        effect=effect or "fade",
        duration=_STYLE_CHANGE_DURATION,
        kind=kind,
    )


class AssemblyError(PipelineError):
    """Failed to assemble reel from segments."""


class ReelAssembler:
    """Concatenate encoded video segments into a single output file via FFmpeg."""

    _TARGET_WIDTH: int = 1080
    _TARGET_HEIGHT: int = 1920

    @staticmethod
    async def _probe_resolution(clip: Path) -> tuple[int, int]:
        """Probe a video clip's resolution via ffprobe.

        Returns ``(width, height)`` or ``(0, 0)`` on any failure.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(clip),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning("ffprobe resolution probe failed: %s", stderr.decode())
                return (0, 0)
            data = json.loads(stdout.decode())
            stream = data["streams"][0]
            return (int(stream["width"]), int(stream["height"]))
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            logger.warning("Failed to parse ffprobe resolution output: %s", exc)
            return (0, 0)

    @staticmethod
    async def _upscale_clip(source: Path, dest: Path) -> Path:
        """Upscale a video clip to 1080x1920 using Lanczos resampling.

        Raises :class:`AssemblyError` on FFmpeg failure.
        """
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-i",
            str(source),
            "-vf",
            "scale=1080:1920:flags=lanczos",
            "-c:a",
            "copy",
            "-y",
            str(dest),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AssemblyError(f"FFmpeg upscale failed (exit {proc.returncode}): {stderr.decode()}")
        logger.info("Upscaled %s -> %s", source.name, dest.name)
        return dest

    async def _ensure_clip_resolution(self, clip_path: Path, temp_dir: Path) -> Path:
        """Return *clip_path* if already 1080x1920, otherwise upscale into *temp_dir*."""
        width, height = await self._probe_resolution(clip_path)
        if width == self._TARGET_WIDTH and height == self._TARGET_HEIGHT:
            logger.debug("Clip %s already at target resolution", clip_path.name)
            return clip_path
        dest = temp_dir / f"_upscaled_{clip_path.stem}.mp4"
        logger.info(
            "Clip %s is %dx%d — upscaling to %dx%d",
            clip_path.name,
            width,
            height,
            self._TARGET_WIDTH,
            self._TARGET_HEIGHT,
        )
        return await self._upscale_clip(clip_path, dest)

    @staticmethod
    def _escape_concat_path(path: Path) -> str:
        """Escape a path for FFmpeg concat demuxer (single quotes -> '\\'')."""
        escaped = str(path.resolve()).replace("'", "'\\''")
        return f"file '{escaped}'"

    @staticmethod
    def _build_xfade_filter(
        segment_count: int,
        transitions: tuple[TransitionSpec, ...],
    ) -> str:
        """Build an xfade filter_complex graph for N segments with transition specs.

        Builds parallel video (xfade) and audio (acrossfade) chains.
        Video: [0:v][1:v]xfade -> [tmp1][2:v]xfade -> ... -> [v]
        Audio: [0:a][1:a]acrossfade -> [atmp1][2:a]acrossfade -> ... -> [a]
        """
        if len(transitions) != segment_count - 1:
            raise AssemblyError(f"Expected {segment_count - 1} transitions, got {len(transitions)}")

        video_parts: list[str] = []
        audio_parts: list[str] = []
        for i, tr in enumerate(transitions):
            # Video chain
            v_src = "[0:v][1:v]" if i == 0 else f"[vtmp{i}][{i + 1}:v]"
            v_out = "[v]" if i == len(transitions) - 1 else f"[vtmp{i + 1}]"
            video_parts.append(
                f"{v_src}xfade=transition={tr.effect}:duration={tr.duration}:offset={tr.offset_seconds}{v_out}"
            )
            # Audio chain
            a_src = "[0:a][1:a]" if i == 0 else f"[atmp{i}][{i + 1}:a]"
            a_out = "[a]" if i == len(transitions) - 1 else f"[atmp{i + 1}]"
            audio_parts.append(f"{a_src}acrossfade=d={tr.duration}{a_out}")

        return ";".join(video_parts + audio_parts)

    async def assemble(
        self,
        segments: list[Path],
        output: Path,
        *,
        transitions: tuple[TransitionSpec, ...] | None = None,
    ) -> Path:
        """Concatenate video segments into a single reel.

        For a single segment, performs a file copy. For multiple segments
        without transitions, uses FFmpeg concat demuxer with stream copy
        (no re-encoding). When transitions are provided, uses xfade
        filter_complex (requires re-encoding at boundaries).
        """
        if not segments:
            raise AssemblyError("segments must not be empty")

        for seg in segments:
            if not seg.exists():
                raise AssemblyError(f"Segment file not found: {seg}")

        output.parent.mkdir(parents=True, exist_ok=True)

        if len(segments) == 1:
            shutil.copy2(segments[0], output)
            return output

        if transitions:
            try:
                return await self._assemble_xfade(segments, output, transitions)
            except AssemblyError:
                logger.warning("xfade assembly failed, falling back to concat")
                return await self._assemble_concat(segments, output)

        return await self._assemble_concat(segments, output)

    async def _assemble_concat(self, segments: list[Path], output: Path) -> Path:
        """Assemble via concat demuxer with stream copy (no re-encoding)."""
        list_file = output.parent / f"_assembly_{output.stem}.txt"
        list_file.write_text("\n".join(self._escape_concat_path(seg) for seg in segments))

        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
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
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise AssemblyError(f"FFmpeg concat failed (exit {proc.returncode}): {stderr.decode()}")
        finally:
            list_file.unlink(missing_ok=True)

        logger.info("Assembled %d segments (concat) into %s", len(segments), output.name)
        return output

    async def _assemble_xfade(
        self,
        segments: list[Path],
        output: Path,
        transitions: tuple[TransitionSpec, ...],
    ) -> Path:
        """Assemble via xfade filter_complex (re-encodes at transition boundaries)."""
        filter_graph = self._build_xfade_filter(len(segments), transitions)

        cmd: list[str] = ["ffmpeg"]
        for seg in segments:
            cmd.extend(["-i", str(seg)])
        cmd.extend(
            [
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                "-y",
                str(output),
            ]
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AssemblyError(f"FFmpeg xfade failed (exit {proc.returncode}): {stderr.decode()}")

        logger.info("Assembled %d segments (xfade) into %s", len(segments), output.name)
        return output

    @staticmethod
    def _build_cutaway_filter(
        base_segment_index: int,
        broll_input_index: int,
        insertion_point_s: float,
        cutaway_duration_s: float,
        fade_duration: float = 0.5,
    ) -> str:
        """Build FFmpeg filter_complex for documentary cutaway overlay.

        The B-roll video replaces the base video at the insertion point
        while the base audio continues uninterrupted.  The overlay fades
        in/out at the boundaries for a polished cutaway look.

        Audio stays as the base segment's audio — no audio from B-roll
        (it is treated as silent visual footage).
        """
        start = insertion_point_s
        end = insertion_point_s + cutaway_duration_s
        fade_out_start = end - fade_duration

        return (
            f"[{broll_input_index}:v]setpts=PTS-STARTPTS,"
            f"scale=1080:1920,"
            f"format=yuva420p,"
            f"fade=t=in:st=0:d={fade_duration}:alpha=1,"
            f"fade=t=out:st={fade_out_start - start}:d={fade_duration}:alpha=1"
            f"[broll{broll_input_index}];"
            f"[{base_segment_index}:v]"
            f"[broll{broll_input_index}]"
            f"overlay=enable='between(t,{start},{end})'"
            f"[v]"
        )

    async def assemble_with_broll(
        self,
        segments: list[Path],
        output: Path,
        broll_placements: tuple[BrollPlacement, ...],
        transitions: tuple[TransitionSpec, ...] | None = None,
    ) -> Path:
        """Assemble segments with documentary cutaway B-roll insertion.

        If *broll_placements* is empty, delegates to :meth:`assemble`.
        For each valid B-roll clip, builds a cutaway overlay filter that
        plays the B-roll video over the base while keeping the base audio.
        Falls back to :meth:`assemble` without B-roll on FFmpeg failure.
        """
        if not broll_placements:
            return await self.assemble(segments, output, transitions=transitions)

        # Validate clip files exist — skip missing ones gracefully
        valid_placements: list[BrollPlacement] = []
        for bp in broll_placements:
            clip = Path(bp.clip_path)
            if clip.exists():
                valid_placements.append(bp)
            else:
                logger.warning("B-roll clip not found, skipping: %s", bp.clip_path)

        if not valid_placements:
            logger.warning("No valid B-roll clips found — assembling without B-roll")
            return await self.assemble(segments, output, transitions=transitions)

        # Ensure all B-roll clips match target resolution before overlay
        upscale_dir = Path(tempfile.mkdtemp(prefix="broll_upscale_"))
        try:
            upscaled_placements: list[BrollPlacement] = []
            for bp in valid_placements:
                new_path = await self._ensure_clip_resolution(Path(bp.clip_path), upscale_dir)
                if str(new_path) != bp.clip_path:
                    upscaled_placements.append(replace(bp, clip_path=str(new_path)))
                else:
                    upscaled_placements.append(bp)

            return await self._assemble_with_cutaways(segments, output, upscaled_placements, transitions)
        except AssemblyError as exc:
            logger.warning("Cutaway assembly failed (%s), falling back to plain assembly", exc.message)
            return await self.assemble(segments, output, transitions=transitions)
        finally:
            shutil.rmtree(upscale_dir, ignore_errors=True)

    async def _assemble_with_cutaways(
        self,
        segments: list[Path],
        output: Path,
        placements: list[BrollPlacement],
        transitions: tuple[TransitionSpec, ...] | None,
    ) -> Path:
        """Internal: build and run the FFmpeg command with cutaway overlays."""
        if not segments:
            raise AssemblyError("segments must not be empty")

        for seg in segments:
            if not seg.exists():
                raise AssemblyError(f"Segment file not found: {seg}")

        output.parent.mkdir(parents=True, exist_ok=True)

        # Build inputs: first all base segments, then B-roll clips
        cmd: list[str] = ["ffmpeg"]
        for seg in segments:
            cmd.extend(["-i", str(seg)])

        broll_start_index = len(segments)
        for bp in placements:
            cmd.extend(["-i", bp.clip_path])

        # Build the base assembly filter (xfade chain or single pass)
        filter_parts: list[str] = []
        base_video_label = "[0:v]"
        base_audio_label = "[0:a]"

        if len(segments) > 1 and transitions:
            # Use xfade for base segments first, then overlay B-roll
            xfade_filter = self._build_xfade_filter(len(segments), transitions)
            filter_parts.append(xfade_filter)
            base_video_label = "[v]"
            base_audio_label = "[a]"

        # For each B-roll, build an overlay on the base video
        current_video = base_video_label
        for i, bp in enumerate(placements):
            broll_idx = broll_start_index + i
            is_last = i == len(placements) - 1
            out_label = "[v]" if is_last else f"[vcut{i}]"

            start = bp.insertion_point_s
            end = bp.insertion_point_s + bp.duration_s
            fade_out_start = bp.duration_s - 0.5

            broll_filter = (
                f"[{broll_idx}:v]setpts=PTS-STARTPTS,"
                f"scale=1080:1920,"
                f"format=yuva420p,"
                f"fade=t=in:st=0:d=0.5:alpha=1,"
                f"fade=t=out:st={fade_out_start}:d=0.5:alpha=1"
                f"[broll{broll_idx}];"
                f"{current_video}"
                f"[broll{broll_idx}]"
                f"overlay=enable='between(t,{start},{end})'"
                f"{out_label}"
            )
            filter_parts.append(broll_filter)
            current_video = out_label

        filter_graph = ";".join(filter_parts)
        cmd.extend(
            [
                "-filter_complex",
                filter_graph,
                "-map",
                "[v]",
                "-map",
                base_audio_label,
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-preset",
                "medium",
                "-c:a",
                "aac",
                "-y",
                str(output),
            ]
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise AssemblyError(f"FFmpeg cutaway failed (exit {proc.returncode}): {stderr.decode()}")

        logger.info(
            "Assembled %d segments with %d B-roll cutaways into %s",
            len(segments),
            len(placements),
            output.name,
        )
        return output

    async def validate_duration(
        self,
        reel: Path,
        min_duration: float = 30.0,
        max_duration: float = 120.0,
    ) -> bool:
        """Validate the assembled reel meets duration requirements via ffprobe."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(reel),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("ffprobe failed: %s", stderr.decode())
            return False

        try:
            duration = float(stdout.decode().strip())
        except ValueError:
            return False

        return min_duration <= duration <= max_duration
