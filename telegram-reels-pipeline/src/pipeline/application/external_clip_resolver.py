"""ExternalClipResolver — search YouTube and download clips for B-roll overlay."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.domain.ports import ExternalClipDownloaderPort

logger = logging.getLogger(__name__)

_MAX_SEARCHES = 3
_INTER_SEARCH_DELAY = 2.0
_MAX_DURATION = 60


class ExternalClipResolver:
    """Resolve Content Creator clip suggestions into downloaded YouTube clips.

    Searches YouTube via yt-dlp ``ytsearch1:`` for each suggestion, prefers
    vertical Shorts under 60 seconds, and downloads matches via the
    ``ExternalClipDownloaderPort``.  All failures are non-fatal: logged and
    skipped so the pipeline continues without external clips.
    """

    def __init__(self, downloader: ExternalClipDownloaderPort) -> None:
        self._downloader = downloader

    async def resolve_all(
        self,
        suggestions: list[dict[str, object]],
        dest_dir: Path,
    ) -> list[dict[str, object]]:
        """Search and download clips for each suggestion, returning resolved metadata.

        Rate-limited: processes at most ``_MAX_SEARCHES`` suggestions with
        ``_INTER_SEARCH_DELAY`` seconds between each search.

        Args:
            suggestions: List of dicts with at least ``search_query`` key.
            dest_dir: Workspace directory where clips are saved.

        Returns:
            List of dicts with ``search_query``, ``url``, ``local_path``, and
            ``duration`` for each successfully resolved clip.
        """
        capped = suggestions[:_MAX_SEARCHES]
        resolved: list[dict[str, object]] = []

        for idx, suggestion in enumerate(capped):
            query = str(suggestion.get("search_query", ""))
            if not query:
                logger.debug("Skipping suggestion with empty search_query")
                continue

            # Rate-limit delay between searches (not before first)
            if idx > 0:
                await asyncio.sleep(_INTER_SEARCH_DELAY)

            try:
                result = await self._resolve_one(query, suggestion, dest_dir)
                if result is not None:
                    resolved.append(result)
            except Exception:
                logger.warning("Failed to resolve suggestion %r — skipping", query, exc_info=True)

        return resolved

    async def write_manifest(self, resolved: list[dict[str, object]], workspace: Path) -> Path:
        """Write resolved clips to ``external-clips.json`` atomically.

        Args:
            resolved: List of resolved clip metadata dicts.
            workspace: Workspace directory.

        Returns:
            Path to the written manifest file.
        """
        manifest_path = workspace / "external-clips.json"
        await asyncio.to_thread(self._write_json_atomic, manifest_path, {"clips": resolved})
        return manifest_path

    async def _resolve_one(
        self,
        query: str,
        suggestion: dict[str, object],
        dest_dir: Path,
    ) -> dict[str, object] | None:
        """Search YouTube for a single query, download if found."""
        search_result = await self._search_youtube(query)
        if search_result is None:
            logger.debug("No YouTube result for %r", query)
            return None

        url = str(search_result["url"])
        duration = search_result.get("duration", 0)

        local_path = await self._downloader.download(url, dest_dir)
        if local_path is None:
            logger.debug("Download failed for %s", url)
            return None

        return {
            "search_query": query,
            "url": url,
            "local_path": str(local_path),
            "duration": duration,
            "label": suggestion.get("label", ""),
            "timing_hint": suggestion.get("timing_hint", ""),
        }

    @staticmethod
    async def _search_youtube(query: str) -> dict[str, object] | None:
        """Search YouTube via yt-dlp ``ytsearch1:``, returning metadata or None.

        Prefers vertical format (Shorts) under 60 seconds duration.
        Returns dict with ``url``, ``duration``, ``width``, ``height`` on success.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "--flat-playlist",
                "--dump-json",
                f"ytsearch1:{query}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
        except OSError as exc:
            logger.warning("yt-dlp search failed to start: %s", exc)
            return None

        if proc.returncode != 0:
            stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
            logger.debug("yt-dlp search returned %d for %r: %s", proc.returncode, query, stderr)
            return None

        if not stdout_bytes:
            return None

        try:
            data = json.loads(stdout_bytes.decode(errors="replace"))
        except json.JSONDecodeError:
            logger.debug("yt-dlp returned non-JSON output for %r", query)
            return None

        url = data.get("url") or data.get("webpage_url") or data.get("original_url", "")
        if not url:
            # Build URL from id if available
            video_id = data.get("id", "")
            if video_id:
                url = f"https://www.youtube.com/watch?v={video_id}"
            else:
                logger.debug("No URL found in yt-dlp result for %r", query)
                return None

        duration = data.get("duration") or 0
        width = data.get("width") or 0
        height = data.get("height") or 0

        # Filter: prefer vertical Shorts under 60s
        if isinstance(duration, (int, float)) and duration > _MAX_DURATION:
            logger.debug("Clip too long (%ss) for %r — skipping", duration, query)
            return None

        return {
            "url": str(url),
            "duration": duration,
            "width": width,
            "height": height,
        }

    @staticmethod
    def _write_json_atomic(path: Path, data: object) -> None:
        """Atomic write: write to tempfile then os.rename()."""
        parent = path.parent
        parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.rename(tmp_path, str(path))
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise
