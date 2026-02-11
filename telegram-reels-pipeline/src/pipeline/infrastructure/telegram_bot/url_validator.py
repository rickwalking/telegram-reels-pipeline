"""YouTube URL validation — pure functions for validating and parsing YouTube URLs."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

# YouTube URL patterns (hostname-based detection)
_YOUTUBE_HOSTS: frozenset[str] = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)

# Video ID: 11 characters, alphanumeric + dash + underscore
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def is_youtube_url(text: str) -> bool:
    """Check whether the given text is a valid YouTube video URL.

    Accepts standard watch URLs, short URLs, and embed URLs.
    Rejects playlists-only, channel pages, and non-video YouTube pages.
    """
    text = text.strip()
    if not text:
        return False

    try:
        parsed = urlparse(text)
    except ValueError:
        return False

    # Must have a scheme (http/https)
    if parsed.scheme not in ("http", "https"):
        return False

    host = parsed.hostname
    if host is None or host.lower() not in _YOUTUBE_HOSTS:
        return False

    return extract_video_id(text) is not None


def extract_video_id(url: str) -> str | None:
    """Extract the 11-character video ID from a YouTube URL.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID

    Returns None if the URL is not a valid YouTube video URL.
    """
    url = url.strip()
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = parsed.hostname
    if host is None:
        return None
    host = host.lower()

    if host not in _YOUTUBE_HOSTS:
        return None

    # Short URL: youtu.be/VIDEO_ID
    if host in ("youtu.be", "www.youtu.be"):
        video_id = parsed.path.lstrip("/").split("/")[0] if parsed.path else ""
        return video_id if _VIDEO_ID_RE.match(video_id) else None

    # Standard URL: youtube.com/watch?v=VIDEO_ID
    if parsed.path == "/watch":
        qs = parse_qs(parsed.query)
        candidates = qs.get("v", [])
        if candidates and _VIDEO_ID_RE.match(candidates[0]):
            return candidates[0]
        return None

    # Embed / v / shorts URLs: youtube.com/embed/VIDEO_ID
    for prefix in ("/embed/", "/v/", "/shorts/"):
        if parsed.path.startswith(prefix):
            video_id = parsed.path[len(prefix) :].split("/")[0]
            return video_id if _VIDEO_ID_RE.match(video_id) else None

    return None
