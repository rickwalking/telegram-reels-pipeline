"""Bootstrap — composition root wiring all adapters to port protocols."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pipeline.app.settings import PipelineSettings
from pipeline.application.crash_recovery import CrashRecoveryHandler
from pipeline.application.delivery_handler import DeliveryHandler
from pipeline.application.event_bus import EventBus
from pipeline.application.layout_escalation import LayoutEscalationHandler
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
from pipeline.infrastructure.adapters.knowledge_base_adapter import YamlKnowledgeBase
from pipeline.infrastructure.adapters.proc_resource_monitor import ProcResourceMonitor
from pipeline.infrastructure.adapters.systemd_watchdog import WatchdogHeartbeat
from pipeline.infrastructure.listeners.event_journal_writer import EventJournalWriter
from pipeline.infrastructure.telegram_bot.bot import TelegramBotAdapter
from pipeline.infrastructure.telegram_bot.polling import TelegramPoller

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
    stage_runner: StageRunner | None = field(default=None)
    pipeline_runner: PipelineRunner | None = field(default=None)
    delivery_handler: DeliveryHandler | None = field(default=None)
    revision_router: RevisionRouter | None = field(default=None)
    revision_handler: RevisionHandler | None = field(default=None)
    layout_escalation: LayoutEscalationHandler | None = field(default=None)
    state_machine: PipelineStateMachine | None = field(default=None)
    crash_recovery: CrashRecoveryHandler | None = field(default=None)
    resource_throttler: ResourceThrottler | None = field(default=None)
    run_cleaner: RunCleaner | None = field(default=None)
    watchdog: WatchdogHeartbeat | None = field(default=None)
    telegram_bot: TelegramBotAdapter | None = field(default=None)
    telegram_poller: TelegramPoller | None = field(default=None)


def create_orchestrator(settings: PipelineSettings | None = None) -> Orchestrator:
    """Wire all adapters and return an Orchestrator ready to run.

    If no settings are provided, loads from environment/.env.
    """
    if settings is None:
        settings = PipelineSettings()

    _validate_settings(settings)

    # Infrastructure adapters
    state_store = FileStateStore(base_dir=settings.workspace_dir / "runs")
    cli_backend = CliBackend(
        work_dir=settings.workspace_dir,
        timeout_seconds=settings.agent_timeout_seconds,
        dispatch_timeout_seconds=max(300.0, settings.agent_timeout_seconds / 2),
        qa_via_clink=settings.qa_via_clink,
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
    journal_writer = EventJournalWriter(log_path=settings.workspace_dir / "events.log")
    event_bus.subscribe(journal_writer)

    # Telegram adapter (optional — requires token and chat_id)
    telegram_bot: TelegramBotAdapter | None = None
    telegram_poller: TelegramPoller | None = None
    if settings.telegram_token and settings.telegram_chat_id:
        from pipeline.infrastructure.listeners.telegram_notifier import TelegramNotifier

        telegram_bot = TelegramBotAdapter(
            token=settings.telegram_token,
            chat_id=settings.telegram_chat_id,
        )
        telegram_poller = TelegramPoller(
            bot=telegram_bot,
            queue=queue_consumer,
            authorized_chat_id=settings.telegram_chat_id,
        )
        # Register Telegram notifier as event listener
        notifier = TelegramNotifier(messaging=telegram_bot)
        event_bus.subscribe(notifier)
        logger.info("Telegram bot connected (chat_id=%s)", settings.telegram_chat_id)
    else:
        logger.warning("Telegram not configured — bot disabled")

    # Stage execution (Epic 9)
    stage_runner = StageRunner(
        reflection_loop=reflection_loop,
        recovery_chain=recovery_chain,
        event_bus=event_bus,
    )
    delivery_handler = DeliveryHandler(messaging=telegram_bot) if telegram_bot else None
    knowledge_base = YamlKnowledgeBase(path=settings.workspace_dir / "crop-strategies.yaml")
    pipeline_runner = PipelineRunner(
        stage_runner=stage_runner,
        state_store=state_store,
        event_bus=event_bus,
        delivery_handler=delivery_handler,
        workflows_dir=settings.workflows_dir,
        cli_backend=cli_backend,
        settings=settings,
    )

    # Revision handling
    revision_router = RevisionRouter(model_dispatch=cli_backend, messaging=telegram_bot)
    revision_handler = RevisionHandler()
    layout_escalation: LayoutEscalationHandler | None = None
    if telegram_bot:
        layout_escalation = LayoutEscalationHandler(messaging=telegram_bot, knowledge_base=knowledge_base)
    state_machine = PipelineStateMachine()

    # Reliability components (Epic 6)
    crash_recovery = CrashRecoveryHandler(state_store=state_store, messaging=telegram_bot)
    resource_monitor = ProcResourceMonitor()
    resource_throttler = ResourceThrottler(monitor=resource_monitor, messaging=telegram_bot)
    run_cleaner = RunCleaner(runs_dir=settings.workspace_dir / "runs")
    watchdog = WatchdogHeartbeat()

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
        stage_runner=stage_runner,
        pipeline_runner=pipeline_runner,
        delivery_handler=delivery_handler,
        revision_router=revision_router,
        revision_handler=revision_handler,
        layout_escalation=layout_escalation,
        state_machine=state_machine,
        crash_recovery=crash_recovery,
        resource_throttler=resource_throttler,
        run_cleaner=run_cleaner,
        watchdog=watchdog,
        telegram_bot=telegram_bot,
        telegram_poller=telegram_poller,
    )


def _validate_settings(settings: PipelineSettings) -> None:
    """Validate critical settings at boot time.

    Raises ConfigurationError if the environment is not viable.
    """
    if settings.telegram_token and not settings.telegram_chat_id:
        raise ConfigurationError("TELEGRAM_CHAT_ID is required when TELEGRAM_TOKEN is set")

    if settings.telegram_chat_id and not settings.telegram_token:
        raise ConfigurationError("TELEGRAM_TOKEN is required when TELEGRAM_CHAT_ID is set")
