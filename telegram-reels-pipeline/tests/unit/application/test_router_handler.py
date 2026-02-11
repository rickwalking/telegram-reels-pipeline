"""Tests for RouterHandler — elicitation flow and smart defaults."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock

from pipeline.application.router_handler import RouterHandler
from pipeline.domain.enums import PipelineStage


def _make_handler(
    messaging: MagicMock | None = None,
    default_topic: str = "",
    default_duration: str = "60-90s",
) -> RouterHandler:
    agent_port = MagicMock()
    return RouterHandler(
        agent_port=agent_port,
        messaging=messaging,
        default_topic_focus=default_topic,
        default_duration_preference=default_duration,
    )


class TestElicitationWithMessaging:
    async def test_asks_two_questions(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(side_effect=["CAP theorem", "90s"])
        handler = _make_handler(messaging=messaging)

        context = await handler.build_elicitation_context("https://youtu.be/test")
        assert context["topic_focus"] == "CAP theorem"
        assert context["duration_preference"] == "90s"
        assert messaging.ask_user.call_count == 2

    async def test_skip_uses_defaults(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(side_effect=["skip", "skip"])
        handler = _make_handler(messaging=messaging, default_topic="", default_duration="60-90s")

        context = await handler.build_elicitation_context("https://youtu.be/test")
        assert context["topic_focus"] == ""
        assert context["duration_preference"] == "60-90s"

    async def test_includes_youtube_url(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(side_effect=["topic", "60s"])
        handler = _make_handler(messaging=messaging)

        context = await handler.build_elicitation_context("https://youtu.be/abc")
        assert context["youtube_url"] == "https://youtu.be/abc"

    async def test_error_falls_back_to_defaults(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock(side_effect=RuntimeError("timeout"))
        handler = _make_handler(messaging=messaging, default_duration="60-90s")

        context = await handler.build_elicitation_context("https://youtu.be/test")
        assert context["topic_focus"] == ""
        assert context["duration_preference"] == "60-90s"


class TestElicitationWithoutMessaging:
    async def test_uses_smart_defaults(self) -> None:
        handler = _make_handler(messaging=None, default_topic="auto", default_duration="75s")

        context = await handler.build_elicitation_context("https://youtu.be/test")
        assert context["topic_focus"] == "auto"
        assert context["duration_preference"] == "75s"

    async def test_includes_url(self) -> None:
        handler = _make_handler()

        context = await handler.build_elicitation_context("https://youtu.be/abc")
        assert context["youtube_url"] == "https://youtu.be/abc"


class TestElicitationWithTopicProvided:
    async def test_skips_questions_when_topic_provided(self) -> None:
        messaging = MagicMock()
        messaging.ask_user = AsyncMock()
        handler = _make_handler(messaging=messaging)

        context = await handler.build_elicitation_context("https://youtu.be/test", topic_focus="AI safety")
        assert context["topic_focus"] == "AI safety"
        messaging.ask_user.assert_not_awaited()

    async def test_uses_default_duration_when_topic_provided(self) -> None:
        handler = _make_handler(default_duration="60-90s")

        context = await handler.build_elicitation_context("https://youtu.be/test", topic_focus="AI")
        assert context["duration_preference"] == "60-90s"


class TestSaveElicitationContext:
    async def test_saves_json_artifact(self, tmp_path: Path) -> None:
        handler = _make_handler()
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "assets").mkdir()

        context = MappingProxyType({"youtube_url": "https://youtu.be/test", "topic_focus": "AI"})
        path = await handler.save_elicitation_context(context, workspace)

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["topic_focus"] == "AI"

    async def test_creates_assets_dir(self, tmp_path: Path) -> None:
        handler = _make_handler()
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        context = MappingProxyType({"youtube_url": "https://youtu.be/test"})
        path = await handler.save_elicitation_context(context, workspace)
        assert path.parent.name == "assets"
        assert path.parent.is_dir()


class TestBuildRouterRequest:
    def test_creates_router_stage_request(self, tmp_path: Path) -> None:
        handler = _make_handler()
        context = MappingProxyType({"youtube_url": "https://youtu.be/test"})
        step = tmp_path / "step.md"
        agent = tmp_path / "agent.md"

        request = handler.build_router_request(context, step, agent)
        assert request.stage == PipelineStage.ROUTER
        assert request.step_file == step
        assert request.agent_definition == agent
        assert request.elicitation_context["youtube_url"] == "https://youtu.be/test"
