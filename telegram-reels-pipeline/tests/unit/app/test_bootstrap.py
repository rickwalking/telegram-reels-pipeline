"""Tests for bootstrap — composition root wiring."""

from __future__ import annotations

from pathlib import Path

from pipeline.app.bootstrap import Orchestrator, create_orchestrator
from pipeline.app.settings import PipelineSettings
from pipeline.application.event_bus import EventBus
from pipeline.application.queue_consumer import QueueConsumer
from pipeline.application.recovery_chain import RecoveryChain
from pipeline.application.reflection_loop import ReflectionLoop
from pipeline.application.workspace_manager import WorkspaceManager
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend
from pipeline.infrastructure.adapters.file_state_store import FileStateStore


class TestCreateOrchestrator:
    def test_returns_orchestrator(self, tmp_path: Path) -> None:
        settings = PipelineSettings(
            workspace_dir=tmp_path / "workspace",
            queue_dir=tmp_path / "queue",
        )
        orch = create_orchestrator(settings)
        assert isinstance(orch, Orchestrator)

    def test_all_components_wired(self, tmp_path: Path) -> None:
        settings = PipelineSettings(
            workspace_dir=tmp_path / "workspace",
            queue_dir=tmp_path / "queue",
        )
        orch = create_orchestrator(settings)
        assert isinstance(orch.event_bus, EventBus)
        assert isinstance(orch.queue_consumer, QueueConsumer)
        assert isinstance(orch.workspace_manager, WorkspaceManager)
        assert isinstance(orch.state_store, FileStateStore)
        assert isinstance(orch.cli_backend, CliBackend)
        assert isinstance(orch.recovery_chain, RecoveryChain)
        assert isinstance(orch.reflection_loop, ReflectionLoop)

    def test_event_bus_has_journal_listener(self, tmp_path: Path) -> None:
        settings = PipelineSettings(
            workspace_dir=tmp_path / "workspace",
            queue_dir=tmp_path / "queue",
        )
        orch = create_orchestrator(settings)
        assert orch.event_bus.listener_count >= 1

    def test_uses_custom_settings(self, tmp_path: Path) -> None:
        settings = PipelineSettings(
            workspace_dir=tmp_path / "custom",
            queue_dir=tmp_path / "q",
            agent_timeout_seconds=600.0,
        )
        orch = create_orchestrator(settings)
        assert orch.settings.agent_timeout_seconds == 600.0

    def test_default_settings_when_none(self) -> None:
        orch = create_orchestrator()
        assert orch.settings is not None
        assert isinstance(orch.settings, PipelineSettings)
