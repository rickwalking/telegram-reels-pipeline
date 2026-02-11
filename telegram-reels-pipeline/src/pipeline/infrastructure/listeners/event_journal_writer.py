"""EventJournalWriter — append pipeline events to events.log."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import aiofiles

from pipeline.domain.models import PipelineEvent

logger = logging.getLogger(__name__)


class EventJournalWriter:
    """Append formatted event entries to a per-run events.log file.

    Format: ``<ISO8601> | <namespace.event_name> | <stage> | <json_data>``
    """

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path

    async def __call__(self, event: PipelineEvent) -> None:
        """Append event to the journal log file."""
        stage_str = event.stage.value if event.stage is not None else "none"
        data_str = json.dumps(dict(event.data), separators=(",", ":"))
        line = f"{event.timestamp} | {event.event_name} | {stage_str} | {data_str}\n"

        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self._log_path, "a") as f:
            await f.write(line)
