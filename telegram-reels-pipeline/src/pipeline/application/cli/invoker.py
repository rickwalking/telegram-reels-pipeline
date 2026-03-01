"""PipelineInvoker — executes Commands and records results in CommandHistory."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.domain.models import CommandRecord

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext
    from pipeline.application.cli.history import CommandHistory
    from pipeline.application.cli.protocols import Command, CommandResult

logger = logging.getLogger(__name__)


class PipelineInvoker:
    """Execute a Command, record the outcome, and persist the history.

    On success: records status ``"success"`` with the result message.
    On exception: records status ``"failed"`` with the error string, then re-raises.
    History is always persisted in a ``finally`` block so debug data survives crashes.
    """

    def __init__(self, history: CommandHistory) -> None:
        self._history = history

    async def execute(self, command: Command, context: PipelineContext) -> CommandResult:
        """Run *command* and record the execution in history.

        Args:
            command: The Command to execute.
            context: Shared pipeline context.

        Returns:
            The CommandResult produced by the command.

        Raises:
            Exception: Re-raises any exception from the command after recording it.
        """
        started_at = datetime.now(UTC).isoformat()
        try:
            result = await command.execute(context)
            finished_at = datetime.now(UTC).isoformat()
            self._history.append(
                CommandRecord(
                    name=command.name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="success",
                )
            )
            return result
        except Exception as exc:
            finished_at = datetime.now(UTC).isoformat()
            self._history.append(
                CommandRecord(
                    name=command.name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status="failed",
                    error=str(exc),
                )
            )
            raise
        finally:
            self._history.persist(context.workspace)
