"""Main entry point — ``python3 -m pipeline.app.main``."""

from __future__ import annotations

import asyncio
import logging
import sys

from pipeline.app.bootstrap import create_orchestrator

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

    logger.info("Pipeline service started — polling queue for work")

    while True:
        claimed = orchestrator.queue_consumer.claim_next()
        if claimed is not None:
            item, processing_path = claimed
            logger.info("Processing queue item: %s", item.url)
            async with orchestrator.workspace_manager.managed_workspace() as workspace:
                logger.info("Workspace created: %s", workspace)
                # Pipeline execution would happen here
                # For now, just log the URL
            orchestrator.queue_consumer.complete(processing_path)
            logger.info("Queue item completed: %s", item.url)
        else:
            await asyncio.sleep(5.0)


def main() -> None:
    """Synchronous entry point for systemd."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Pipeline service shutting down")


if __name__ == "__main__":
    main()
