"""Tests for PipelineSettings — configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.app.settings import PipelineSettings


class TestPipelineSettings:
    def test_default_values(self) -> None:
        settings = PipelineSettings(
            telegram_token="test-token",
            telegram_chat_id="12345",
        )
        assert settings.workspace_dir == Path("workspace")
        assert settings.queue_dir == Path("queue")
        assert settings.agent_timeout_seconds == 300.0
        assert settings.min_qa_score == 40

    def test_custom_values(self) -> None:
        settings = PipelineSettings(
            telegram_token="token",
            telegram_chat_id="chat",
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

    def test_publishing_defaults(self) -> None:
        settings = PipelineSettings()
        assert settings.publishing_language == ""
        assert settings.publishing_description_variants == 3

    def test_publishing_custom_values(self) -> None:
        settings = PipelineSettings(
            publishing_language="pt-BR",
            publishing_description_variants=5,
        )
        assert settings.publishing_language == "pt-BR"
        assert settings.publishing_description_variants == 5

    def test_publishing_variants_min_max(self) -> None:
        settings_min = PipelineSettings(publishing_description_variants=1)
        assert settings_min.publishing_description_variants == 1
        settings_max = PipelineSettings(publishing_description_variants=10)
        assert settings_max.publishing_description_variants == 10

    def test_publishing_variants_below_min_raises(self) -> None:
        with pytest.raises(ValidationError):
            PipelineSettings(publishing_description_variants=0)

    def test_publishing_variants_above_max_raises(self) -> None:
        with pytest.raises(ValidationError):
            PipelineSettings(publishing_description_variants=11)
