"""RouterHandler — router stage elicitation flow and smart defaults."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest

if TYPE_CHECKING:
    from pipeline.domain.ports import AgentExecutionPort, MessagingPort

logger = logging.getLogger(__name__)

# Smart defaults when user provides no context
DEFAULT_TOPIC_FOCUS: str = ""
DEFAULT_DURATION_PREFERENCE: str = "60-90s"

# Elicitation questions
_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("topic_focus", "Any specific topic or moment you want to highlight? (or 'skip' to use the best moment)"),
    ("duration_preference", "Preferred clip length? (e.g., '60s', '90s', or 'skip' for default 60-90s)"),
)


class RouterHandler:
    """Handle the Router stage with optional user elicitation.

    The router stage is special: before running the AI agent, it can ask the user
    0-2 clarifying questions via Telegram. If messaging is unavailable or the user
    skips, smart defaults are applied.
    """

    def __init__(
        self,
        agent_port: AgentExecutionPort,
        messaging: MessagingPort | None = None,
        default_topic_focus: str = DEFAULT_TOPIC_FOCUS,
        default_duration_preference: str = DEFAULT_DURATION_PREFERENCE,
    ) -> None:
        self._agent_port = agent_port
        self._messaging = messaging
        self._default_topic_focus = default_topic_focus
        self._default_duration_preference = default_duration_preference

    async def build_elicitation_context(
        self,
        youtube_url: str,
        topic_focus: str | None = None,
    ) -> Mapping[str, str]:
        """Gather elicitation context through Telegram questions or smart defaults.

        If topic_focus is already provided (from queue item), skips the first question.
        Returns a frozen mapping of elicitation key-value pairs.
        """
        context: dict[str, str] = {
            "youtube_url": youtube_url,
        }

        if topic_focus:
            context["topic_focus"] = topic_focus
            context["duration_preference"] = self._default_duration_preference
            logger.info("Using provided topic focus: %s", topic_focus)
        elif self._messaging is not None:
            context.update(await self._ask_questions())
        else:
            context["topic_focus"] = self._default_topic_focus
            context["duration_preference"] = self._default_duration_preference
            logger.info("No messaging available — using smart defaults")

        return MappingProxyType(context)

    async def _ask_questions(self) -> dict[str, str]:
        """Ask elicitation questions via Telegram and collect responses."""
        assert self._messaging is not None
        answers: dict[str, str] = {}

        for key, question in _QUESTIONS:
            try:
                response = await self._messaging.ask_user(question)
                response = response.strip()
                if response.lower() in ("skip", "s", ""):
                    answers[key] = self._get_default(key)
                    logger.info("User skipped question '%s' — using default", key)
                else:
                    answers[key] = response
                    logger.info("User answered '%s': %s", key, response)
            except Exception:
                answers[key] = self._get_default(key)
                logger.warning("Failed to get answer for '%s' — using default", key, exc_info=True)

        return answers

    def _get_default(self, key: str) -> str:
        """Get the smart default for a given elicitation key."""
        if key == "topic_focus":
            return self._default_topic_focus
        if key == "duration_preference":
            return self._default_duration_preference
        return ""

    async def save_elicitation_context(
        self,
        context: Mapping[str, str],
        workspace: Path,
    ) -> Path:
        """Save elicitation context as a JSON artifact in the workspace.

        Returns the path to the saved artifact.
        """
        artifact_path = workspace / "assets" / "elicitation-context.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        data = dict(context)
        artifact_path.write_text(json.dumps(data, indent=2))
        logger.info("Saved elicitation context to %s", artifact_path)
        return artifact_path

    def build_router_request(
        self,
        context: Mapping[str, str],
        step_file: Path,
        agent_definition: Path,
    ) -> AgentRequest:
        """Build an AgentRequest for the router stage with elicitation context."""
        return AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=step_file,
            agent_definition=agent_definition,
            elicitation_context=context,
        )
