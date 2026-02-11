"""Tests for YouTube URL validator — pure validation functions."""

from __future__ import annotations

from pipeline.infrastructure.telegram_bot.url_validator import extract_video_id, is_youtube_url


class TestIsYoutubeUrl:
    def test_standard_watch_url(self) -> None:
        assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_short_url(self) -> None:
        assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_embed_url(self) -> None:
        assert is_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ") is True

    def test_shorts_url(self) -> None:
        assert is_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ") is True

    def test_v_url(self) -> None:
        assert is_youtube_url("https://www.youtube.com/v/dQw4w9WgXcQ") is True

    def test_mobile_url(self) -> None:
        assert is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_http_url(self) -> None:
        assert is_youtube_url("http://youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_url_with_extra_params(self) -> None:
        assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42") is True

    def test_url_with_whitespace(self) -> None:
        assert is_youtube_url("  https://youtu.be/dQw4w9WgXcQ  ") is True

    def test_rejects_empty_string(self) -> None:
        assert is_youtube_url("") is False

    def test_rejects_plain_text(self) -> None:
        assert is_youtube_url("hello world") is False

    def test_rejects_non_youtube_url(self) -> None:
        assert is_youtube_url("https://www.google.com") is False

    def test_rejects_youtube_channel(self) -> None:
        assert is_youtube_url("https://www.youtube.com/@channelname") is False

    def test_rejects_youtube_homepage(self) -> None:
        assert is_youtube_url("https://www.youtube.com/") is False

    def test_rejects_watch_without_v(self) -> None:
        assert is_youtube_url("https://www.youtube.com/watch") is False

    def test_rejects_no_scheme(self) -> None:
        assert is_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ") is False

    def test_rejects_invalid_video_id(self) -> None:
        assert is_youtube_url("https://youtu.be/short") is False

    def test_rejects_instagram_url(self) -> None:
        assert is_youtube_url("https://www.instagram.com/reel/123") is False


class TestExtractVideoId:
    def test_standard_watch_url(self) -> None:
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self) -> None:
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self) -> None:
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self) -> None:
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_v_url(self) -> None:
        assert extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_returns_none_for_non_youtube(self) -> None:
        assert extract_video_id("https://www.google.com") is None

    def test_returns_none_for_channel(self) -> None:
        assert extract_video_id("https://www.youtube.com/@channel") is None

    def test_returns_none_for_empty(self) -> None:
        assert extract_video_id("") is None

    def test_returns_none_for_invalid_id(self) -> None:
        assert extract_video_id("https://youtu.be/bad") is None

    def test_url_with_extra_params_preserves_id(self) -> None:
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest") == "dQw4w9WgXcQ"
