"""Tests for PipelineSettings — configuration loading."""

from __future__ import annotations

from pathlib import Path

from pipeline.app.settings import PipelineSettings


class TestPipelineSettings:
    def test_default_values(self) -> None:
        settings = PipelineSettings(
            telegram_token="test-token",
            telegram_chat_id="12345",
            anthropic_api_key="sk-test",
        )
        assert settings.workspace_dir == Path("workspace")
        assert settings.queue_dir == Path("queue")
        assert settings.agent_timeout_seconds == 300.0
        assert settings.min_qa_score == 40

    def test_custom_values(self) -> None:
        settings = PipelineSettings(
            telegram_token="token",
            telegram_chat_id="chat",
            anthropic_api_key="key",
            workspace_dir=Path("/custom/workspace"),
            queue_dir=Path("/custom/queue"),
            agent_timeout_seconds=600.0,
            min_qa_score=50,
        )
        assert settings.workspace_dir == Path("/custom/workspace")
        assert settings.agent_timeout_seconds == 600.0
        assert settings.min_qa_score == 50

    def test_empty_defaults(self) -> None:
        settings = PipelineSettings()
        assert settings.telegram_token == ""
        assert settings.telegram_chat_id == ""
        assert settings.anthropic_api_key == ""
