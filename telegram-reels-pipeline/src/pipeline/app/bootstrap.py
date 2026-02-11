"""Bootstrap — composition root wiring all adapters to port protocols."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pipeline.app.settings import PipelineSettings
from pipeline.application.event_bus import EventBus
from pipeline.application.queue_consumer import QueueConsumer
from pipeline.application.recovery_chain import RecoveryChain
from pipeline.application.reflection_loop import ReflectionLoop
from pipeline.application.workspace_manager import WorkspaceManager
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend
from pipeline.infrastructure.adapters.file_state_store import FileStateStore
from pipeline.infrastructure.listeners.event_journal_writer import EventJournalWriter

logger = logging.getLogger(__name__)


@dataclass
class Orchestrator:
    """Container for all wired pipeline components.

    Not a frozen dataclass — components are mutable singletons.
    """

    settings: PipelineSettings
    event_bus: EventBus
    queue_consumer: QueueConsumer
    workspace_manager: WorkspaceManager
    state_store: FileStateStore
    cli_backend: CliBackend
    recovery_chain: RecoveryChain
    reflection_loop: ReflectionLoop


def create_orchestrator(settings: PipelineSettings | None = None) -> Orchestrator:
    """Wire all adapters and return an Orchestrator ready to run.

    If no settings are provided, loads from environment/.env.
    """
    if settings is None:
        settings = PipelineSettings()

    # Infrastructure adapters
    state_store = FileStateStore(base_dir=settings.workspace_dir / "runs")
    cli_backend = CliBackend(
        work_dir=settings.workspace_dir,
        timeout_seconds=settings.agent_timeout_seconds,
    )

    # Application components
    event_bus = EventBus()
    queue_consumer = QueueConsumer(base_dir=settings.queue_dir)
    workspace_manager = WorkspaceManager(base_dir=settings.workspace_dir)
    recovery_chain = RecoveryChain(agent_port=cli_backend)
    reflection_loop = ReflectionLoop(
        agent_port=cli_backend,
        model_port=cli_backend,
        min_score_threshold=settings.min_qa_score,
    )

    # Register default listeners
    # Note: telegram_notifier and frontmatter_checkpointer are registered
    # when messaging port is available (requires Telegram bot connection)
    journal_writer = EventJournalWriter(log_path=settings.workspace_dir / "events.log")
    event_bus.subscribe(journal_writer)

    logger.info(
        "Orchestrator created: workspace=%s, queue=%s, timeout=%.0fs",
        settings.workspace_dir,
        settings.queue_dir,
        settings.agent_timeout_seconds,
    )

    return Orchestrator(
        settings=settings,
        event_bus=event_bus,
        queue_consumer=queue_consumer,
        workspace_manager=workspace_manager,
        state_store=state_store,
        cli_backend=cli_backend,
        recovery_chain=recovery_chain,
        reflection_loop=reflection_loop,
    )
