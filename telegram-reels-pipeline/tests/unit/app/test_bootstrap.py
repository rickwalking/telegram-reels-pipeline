"""Tests for bootstrap — composition root wiring."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.app.bootstrap import Orchestrator, create_orchestrator
from pipeline.app.settings import PipelineSettings
from pipeline.application.crash_recovery import CrashRecoveryHandler
from pipeline.application.delivery_handler import DeliveryHandler
from pipeline.application.event_bus import EventBus
from pipeline.application.pipeline_runner import PipelineRunner
from pipeline.application.queue_consumer import QueueConsumer
from pipeline.application.recovery_chain import RecoveryChain
from pipeline.application.reflection_loop import ReflectionLoop
from pipeline.application.resource_throttler import ResourceThrottler
from pipeline.application.revision_handler import RevisionHandler
from pipeline.application.revision_router import RevisionRouter
from pipeline.application.run_cleanup import RunCleaner
from pipeline.application.stage_runner import StageRunner
from pipeline.application.state_machine import PipelineStateMachine
from pipeline.application.workspace_manager import WorkspaceManager
from pipeline.domain.errors import ConfigurationError
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend
from pipeline.infrastructure.adapters.file_state_store import FileStateStore
from pipeline.infrastructure.adapters.systemd_watchdog import WatchdogHeartbeat


def _settings(tmp_path: Path, **overrides: object) -> PipelineSettings:
    defaults: dict[str, object] = {
        "workspace_dir": tmp_path / "workspace",
        "queue_dir": tmp_path / "queue",
    }
    defaults.update(overrides)
    return PipelineSettings(**defaults)


class TestCreateOrchestrator:
    def test_returns_orchestrator(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path))
        assert isinstance(orch, Orchestrator)

    def test_all_core_components_wired(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path))
        assert isinstance(orch.event_bus, EventBus)
        assert isinstance(orch.queue_consumer, QueueConsumer)
        assert isinstance(orch.workspace_manager, WorkspaceManager)
        assert isinstance(orch.state_store, FileStateStore)
        assert isinstance(orch.cli_backend, CliBackend)
        assert isinstance(orch.recovery_chain, RecoveryChain)
        assert isinstance(orch.reflection_loop, ReflectionLoop)

    def test_epic9_components_wired(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path))
        assert isinstance(orch.stage_runner, StageRunner)
        assert isinstance(orch.pipeline_runner, PipelineRunner)
        assert isinstance(orch.revision_router, RevisionRouter)
        assert isinstance(orch.revision_handler, RevisionHandler)
        assert isinstance(orch.state_machine, PipelineStateMachine)
        assert isinstance(orch.crash_recovery, CrashRecoveryHandler)
        assert isinstance(orch.resource_throttler, ResourceThrottler)
        assert isinstance(orch.run_cleaner, RunCleaner)
        assert isinstance(orch.watchdog, WatchdogHeartbeat)

    def test_delivery_handler_none_without_telegram(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path))
        assert orch.delivery_handler is None
        assert orch.layout_escalation is None

    def test_delivery_handler_wired_with_telegram(self, tmp_path: Path) -> None:
        orch = create_orchestrator(
            _settings(
                tmp_path,
                telegram_token="tok",
                telegram_chat_id="123",
            )
        )
        assert isinstance(orch.delivery_handler, DeliveryHandler)

    def test_event_bus_has_journal_listener(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path))
        assert orch.event_bus.listener_count >= 1

    def test_uses_custom_settings(self, tmp_path: Path) -> None:
        orch = create_orchestrator(_settings(tmp_path, agent_timeout_seconds=600.0))
        assert orch.settings.agent_timeout_seconds == 600.0


class TestBootValidation:
    def test_raises_token_without_chat_id(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError, match="TELEGRAM_CHAT_ID"):
            create_orchestrator(_settings(tmp_path, telegram_token="tok", telegram_chat_id=""))

    def test_raises_chat_id_without_token(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError, match="TELEGRAM_TOKEN"):
            create_orchestrator(_settings(tmp_path, telegram_token="", telegram_chat_id="123"))
