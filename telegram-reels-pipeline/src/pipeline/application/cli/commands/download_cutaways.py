"""DownloadCutawaysCommand — download external cutaway clips and write manifest."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.protocols import ClipDurationProber, Command, CommandResult
    from pipeline.domain.ports import ExternalClipDownloaderPort

logger = logging.getLogger(__name__)


def parse_cutaway_spec(spec: str) -> tuple[str, float]:
    """Parse a ``URL@TIMESTAMP`` cutaway spec by splitting on the **last** ``@``.

    URLs may contain ``@`` characters (e.g. ``https://example.com/@user/video``),
    so we split on the rightmost ``@`` to separate the insertion timestamp.

    Returns:
        ``(url, timestamp_seconds)`` tuple.

    Raises:
        ValueError: If no ``@`` found, ``@`` is first character, or timestamp is
            not a valid float.
    """
    idx = spec.rfind("@")
    if idx <= 0:
        raise ValueError(f"Invalid cutaway spec '{spec}': expected URL@TIMESTAMP")
    url = spec[:idx]
    try:
        timestamp = float(spec[idx + 1 :])
    except ValueError:
        raise ValueError(f"Invalid cutaway timestamp in '{spec}': expected a number after '@'") from None
    if timestamp < 0:
        raise ValueError(f"Invalid cutaway timestamp {timestamp}: must be >= 0")
    return url, timestamp


async def _download_cutaway_clips(
    cutaway_specs: list[str],
    workspace: Path,
    clip_downloader: ExternalClipDownloaderPort,
    duration_prober: ClipDurationProber,
) -> list[dict[str, object]]:
    """Download cutaway clips and write ``external-clips.json`` manifest.

    Downloads each clip via the injected ``clip_downloader``, renames to
    ``cutaway-{n}.mp4``, probes duration, and builds a manifest array.
    Partial failures are tolerated: failed downloads are logged and skipped.

    Returns:
        List of manifest entries (one per successfully downloaded clip).
    """
    import shutil

    manifest: list[dict[str, object]] = []
    clips_dir = workspace / "external_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    for idx, spec in enumerate(cutaway_specs):
        try:
            url, insertion_point = parse_cutaway_spec(spec)
        except ValueError as exc:
            logger.warning("Skipping invalid cutaway spec: %s", exc)
            print(f"    [CUTAWAY] Skipping invalid spec: {exc}")
            continue

        print(f"    [CUTAWAY] Downloading clip {idx + 1}/{len(cutaway_specs)}: {url}")
        downloaded = await clip_downloader.download(url, workspace)
        if downloaded is None:
            logger.warning("Cutaway download failed for %s -- skipping", url)
            print(f"    [CUTAWAY] Download failed for {url} -- skipping")
            continue

        # Rename to canonical cutaway-{n}.mp4
        dest = clips_dir / f"cutaway-{idx}.mp4"
        try:
            downloaded.rename(dest)
        except OSError:
            # Cross-device rename -- fall back to copy + unlink
            shutil.copy2(str(downloaded), str(dest))
            with contextlib.suppress(OSError):
                downloaded.unlink()

        duration = await duration_prober.probe(dest)
        if duration is None:
            logger.warning("Could not probe duration for %s -- skipping", dest.name)
            print(f"    [CUTAWAY] Could not probe duration for {dest.name} -- skipping")
            continue

        entry: dict[str, object] = {
            "url": url,
            "clip_path": f"external_clips/cutaway-{idx}.mp4",
            "insertion_point_s": insertion_point,
            "duration_s": duration,
        }
        manifest.append(entry)
        print(f"    [CUTAWAY] Ready: cutaway-{idx}.mp4 ({duration:.1f}s, insert at {insertion_point:.1f}s)")

    # Write manifest (atomic write)
    manifest_path = workspace / "external-clips.json"
    fd, tmp_path_str = tempfile.mkstemp(dir=str(workspace), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        os.replace(tmp_path_str, str(manifest_path))
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path_str)
        raise

    logger.info("Wrote external-clips.json with %d entries", len(manifest))
    return manifest


class DownloadCutawaysCommand:
    """Download external cutaway clips and write manifest."""

    if TYPE_CHECKING:
        _protocol_check: Command

    def __init__(
        self,
        clip_downloader: ExternalClipDownloaderPort,
        duration_prober: ClipDurationProber,
    ) -> None:
        self._clip_downloader = clip_downloader
        self._duration_prober = duration_prober

    @property
    def name(self) -> str:
        return "download-cutaways"

    async def execute(self, context: PipelineContext) -> CommandResult:
        """Download cutaway clips if any are specified in context state.

        Reads ``cutaway_specs`` from ``context.state["cutaway_specs"]``.
        If none, returns early with success. Otherwise downloads clips,
        writes the manifest via atomic write, and returns a summary.
        """
        from pipeline.application.cli.protocols import CommandResult

        cutaway_specs: list[str] | None = context.state.get("cutaway_specs")
        if not cutaway_specs:
            return CommandResult(success=True, message="No cutaway clips specified")

        workspace = context.require_workspace()

        print(f"  Downloading {len(cutaway_specs)} cutaway clip(s)...")
        manifest = await _download_cutaway_clips(
            cutaway_specs,
            workspace,
            self._clip_downloader,
            self._duration_prober,
        )
        print(f"  Cutaway clips ready: {len(manifest)}/{len(cutaway_specs)} succeeded\n")

        return CommandResult(
            success=True,
            message=f"Downloaded {len(manifest)}/{len(cutaway_specs)} cutaway clips",
            data={"manifest_count": len(manifest), "specs_count": len(cutaway_specs)},
        )
