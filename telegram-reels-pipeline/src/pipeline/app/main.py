"""Main entry point — ``python3 -m pipeline.app.main``."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from pipeline.app.bootstrap import Orchestrator, create_orchestrator
from pipeline.domain.enums import EscalationState
from pipeline.domain.errors import PipelineError
from pipeline.domain.models import QueueItem
from pipeline.infrastructure.adapters.systemd_watchdog import notify_ready, notify_stopping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


async def _resume_interrupted_runs(orchestrator: Orchestrator) -> None:
    """Resume any interrupted runs discovered by crash recovery."""
    if orchestrator.crash_recovery is None or orchestrator.pipeline_runner is None:
        return

    plans = await orchestrator.crash_recovery.scan_and_recover()
    for plan in plans:
        workspace_path = plan.run_state.workspace_path
        if not workspace_path:
            logger.warning("Run %s has no workspace_path — skipping resume", plan.run_state.run_id)
            continue

        workspace = Path(workspace_path)
        if not workspace.is_dir():
            logger.warning("Workspace %s no longer exists — skipping resume of %s", workspace, plan.run_state.run_id)
            continue

        logger.info("Resuming run %s from %s", plan.run_state.run_id, plan.resume_from.value)
        try:
            await orchestrator.pipeline_runner.resume(plan.run_state, plan.resume_from, workspace)
        except PipelineError as exc:
            logger.error("Failed to resume run %s: %s", plan.run_state.run_id, exc)
        except Exception:
            logger.exception("Unexpected error resuming run %s", plan.run_state.run_id)


async def run() -> None:
    """Bootstrap the orchestrator and run the queue consumer loop."""
    orchestrator = create_orchestrator()
    orchestrator.queue_consumer.ensure_dirs()

    # Crash recovery — resume interrupted runs
    await _resume_interrupted_runs(orchestrator)

    # Start watchdog heartbeat for systemd
    if orchestrator.watchdog is not None:
        orchestrator.watchdog.start()

    # Signal systemd that the service is ready
    notify_ready()

    logger.info("Pipeline service started — polling queue for work")

    try:
        while True:
            # Poll Telegram for new messages (if configured)
            if orchestrator.telegram_poller is not None:
                await orchestrator.telegram_poller.poll_once()

            claimed = orchestrator.queue_consumer.claim_next()
            if claimed is not None:
                item, processing_path = claimed
                logger.info("Processing queue item: %s", item.url)

                # Check resources before heavy processing
                if orchestrator.resource_throttler is not None:
                    await orchestrator.resource_throttler.wait_for_resources()

                await _process_item(orchestrator, item, processing_path)
            else:
                await asyncio.sleep(5.0)
    finally:
        # Stop watchdog heartbeat
        if orchestrator.watchdog is not None:
            await orchestrator.watchdog.stop()

        notify_stopping()
        logger.info("Pipeline service stopped")


async def _process_item(orchestrator: Orchestrator, item: QueueItem, processing_path: Path) -> None:
    """Execute the pipeline for a single queue item with error handling."""
    if orchestrator.pipeline_runner is None:
        logger.error("PipelineRunner not configured — cannot process items")
        orchestrator.queue_consumer.fail(processing_path)
        return

    try:
        async with orchestrator.workspace_manager.managed_workspace() as workspace:
            logger.info("Workspace created: %s", workspace)
            state = await orchestrator.pipeline_runner.run(item, workspace)

        # If escalation is active, leave item in processing/ for resume
        if state.escalation_state != EscalationState.NONE:
            logger.warning("Run escalated (%s) — leaving in processing for resume", state.escalation_state.value)
            return

        orchestrator.queue_consumer.complete(processing_path)
        logger.info("Queue item completed: %s", item.url)

    except PipelineError as exc:
        logger.error("Pipeline failed for %s: %s", item.url, exc)
        orchestrator.queue_consumer.fail(processing_path)
        if orchestrator.telegram_bot is not None:
            try:
                await orchestrator.telegram_bot.notify_user(f"Pipeline failed: {exc.message}")
            except Exception:
                logger.exception("Failed to send error notification")

    except Exception:
        logger.exception("Unexpected error processing %s", item.url)
        orchestrator.queue_consumer.fail(processing_path)
        if orchestrator.telegram_bot is not None:
            try:
                await orchestrator.telegram_bot.notify_user("Pipeline encountered an unexpected error.")
            except Exception:
                logger.exception("Failed to send error notification")


def main() -> None:
    """Synchronous entry point for systemd."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Pipeline service shutting down")


if __name__ == "__main__":
    main()
