"""Pipeline settings — Pydantic BaseSettings for configuration from .env and YAML."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class PipelineSettings(BaseSettings):
    """Pipeline configuration loaded from environment variables and .env file.

    All secrets (tokens, API keys) come from environment.
    Non-secret config comes from YAML files loaded separately.
    """

    # Telegram
    telegram_token: str = Field(default="", description="Telegram Bot API token")
    telegram_chat_id: str = Field(default="", description="Authorized Telegram chat ID")

    # Paths
    workspace_dir: Path = Field(default=Path("workspace"), description="Base directory for run workspaces")
    queue_dir: Path = Field(default=Path("queue"), description="Base directory for FIFO queue")
    config_dir: Path = Field(default=Path("config"), description="Runtime YAML configuration directory")
    workflows_dir: Path = Field(default=Path("workflows"), description="BMAD workflow stage definitions")

    # Agent execution
    agent_timeout_seconds: float = Field(default=300.0, description="Timeout for agent subprocess execution")

    # QA
    min_qa_score: int = Field(default=40, description="Minimum QA score before escalation")

    # Elicitation defaults
    default_topic_focus: str = Field(default="", description="Default topic focus when user skips elicitation")
    default_duration_preference: str = Field(default="60-90s", description="Default clip duration preference")

    # Publishing
    publishing_language: str = Field(
        default="", description="Target language for descriptions/hashtags (e.g., pt-BR). Empty = skip"
    )
    publishing_description_variants: int = Field(default=3, ge=1, le=10, description="Number of description variants")

    model_config = {"env_prefix": "", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
