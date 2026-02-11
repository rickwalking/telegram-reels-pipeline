"""Tests for PromptBuilder — prompt construction from AgentRequest."""

from pathlib import Path
from types import MappingProxyType

import pytest

from pipeline.application.prompt_builder import build_agent_prompt
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest


@pytest.fixture
def step_file(tmp_path: Path) -> Path:
    f = tmp_path / "stage-01-router.md"
    f.write_text("Route the YouTube URL to the correct pipeline path.")
    return f


@pytest.fixture
def agent_def(tmp_path: Path) -> Path:
    f = tmp_path / "agent.md"
    f.write_text("You are the Router Agent. Analyze the URL and decide the pipeline flow.")
    return f


class TestBuildAgentPrompt:
    def test_includes_step_file_content(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "Route the YouTube URL" in prompt

    def test_includes_agent_definition_content(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "You are the Router Agent" in prompt

    def test_includes_section_headers(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "## Stage Requirements" in prompt
        assert "## Agent Definition" in prompt

    def test_includes_prior_artifact_paths(self, step_file: Path, agent_def: Path, tmp_path: Path) -> None:
        artifact1 = tmp_path / "research.md"
        artifact2 = tmp_path / "transcript.md"
        request = AgentRequest(
            stage=PipelineStage.CONTENT,
            step_file=step_file,
            agent_definition=agent_def,
            prior_artifacts=(artifact1, artifact2),
        )
        prompt = build_agent_prompt(request)
        assert "## Prior Artifacts" in prompt
        assert str(artifact1) in prompt
        assert str(artifact2) in prompt

    def test_includes_elicitation_context(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(
            stage=PipelineStage.ROUTER,
            step_file=step_file,
            agent_definition=agent_def,
            elicitation_context=MappingProxyType({"topic_focus": "AI safety", "tone": "casual"}),
        )
        prompt = build_agent_prompt(request)
        assert "## Elicitation Context" in prompt
        assert "topic_focus: AI safety" in prompt
        assert "tone: casual" in prompt

    def test_includes_attempt_history(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(
            stage=PipelineStage.RESEARCH,
            step_file=step_file,
            agent_definition=agent_def,
            attempt_history=(
                MappingProxyType({"score": "45", "feedback": "Missing key details"}),
                MappingProxyType({"score": "72", "feedback": "Better but needs sources"}),
            ),
        )
        prompt = build_agent_prompt(request)
        assert "## Attempt History" in prompt
        assert "### Attempt 1" in prompt
        assert "### Attempt 2" in prompt
        assert "Missing key details" in prompt
        assert "Better but needs sources" in prompt

    def test_omits_empty_prior_artifacts(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "## Prior Artifacts" not in prompt

    def test_omits_empty_elicitation_context(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "## Elicitation Context" not in prompt

    def test_omits_empty_attempt_history(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert "## Attempt History" not in prompt

    def test_minimal_request_has_two_sections(self, step_file: Path, agent_def: Path) -> None:
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        prompt = build_agent_prompt(request)
        assert prompt.count("## ") == 2
