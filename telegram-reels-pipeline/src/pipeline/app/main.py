"""Main entry point — ``python3 -m pipeline.app.main``."""

from __future__ import annotations

import asyncio
import logging
import sys

from pipeline.app.bootstrap import create_orchestrator
from pipeline.infrastructure.adapters.systemd_watchdog import notify_ready, notify_stopping

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


async def run() -> None:
    """Bootstrap the orchestrator and run the queue consumer loop."""
    orchestrator = create_orchestrator()
    orchestrator.queue_consumer.ensure_dirs()

    # Crash recovery — resume interrupted runs
    if orchestrator.crash_recovery is not None:
        plans = await orchestrator.crash_recovery.scan_and_recover()
        if plans:
            logger.info("Found %d interrupted run(s) to resume", len(plans))

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

                async with orchestrator.workspace_manager.managed_workspace() as workspace:
                    logger.info("Workspace created: %s", workspace)
                    # Pipeline execution would happen here
                    # For now, just log the URL
                orchestrator.queue_consumer.complete(processing_path)
                logger.info("Queue item completed: %s", item.url)
            else:
                await asyncio.sleep(5.0)
    finally:
        # Stop watchdog heartbeat
        if orchestrator.watchdog is not None:
            await orchestrator.watchdog.stop()

        notify_stopping()
        logger.info("Pipeline service stopped")


def main() -> None:
    """Synchronous entry point for systemd."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Pipeline service shutting down")


if __name__ == "__main__":
    main()
