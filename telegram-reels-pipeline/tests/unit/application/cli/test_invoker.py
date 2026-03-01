"""Tests for PipelineInvoker — happy path, exception recording, history persistence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from unittest.mock import MagicMock

import pytest

from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.history import CommandHistory
from pipeline.application.cli.invoker import PipelineInvoker
from pipeline.application.cli.protocols import CommandResult

# --- Helpers ---


@dataclass
class _StubCommand:
    """Concrete command stub for testing."""

    _name: str = "test-command"
    _result: CommandResult | None = None
    _error: Exception | None = None

    @property
    def name(self) -> str:
        return self._name

    async def execute(self, context: PipelineContext) -> CommandResult:
        if self._error is not None:
            raise self._error
        if self._result is not None:
            return self._result
        return CommandResult(success=True, message="ok")


def _make_context(workspace: Path | None = None) -> PipelineContext:
    return PipelineContext(
        settings=MagicMock(),
        stage_runner=MagicMock(),
        event_bus=MagicMock(),
        workspace=workspace,
    )


def _make_invoker(history: CommandHistory | None = None) -> PipelineInvoker:
    if history is None:
        history = CommandHistory()
    return PipelineInvoker(history=history)


# --- Tests ---


class TestPipelineInvokerHappyPath:
    """Verify successful command execution and recording."""

    @pytest.mark.asyncio
    async def test_returns_command_result(self) -> None:
        """Invoker returns the CommandResult from the command."""
        expected = CommandResult(success=True, message="done", data=MappingProxyType({"key": "val"}))
        cmd = _StubCommand(_result=expected)
        invoker = _make_invoker()
        ctx = _make_context()

        result = await invoker.execute(cmd, ctx)

        assert result is expected

    @pytest.mark.asyncio
    async def test_records_success_in_history(self) -> None:
        """Successful execution records a 'success' entry."""
        history = CommandHistory()
        invoker = _make_invoker(history)
        ctx = _make_context()

        await invoker.execute(_StubCommand(_name="my-cmd"), ctx)

        records = history.all()
        assert len(records) == 1
        assert records[0].name == "my-cmd"
        assert records[0].status == "success"
        assert records[0].error is None
        assert records[0].started_at != ""
        assert records[0].finished_at != ""

    @pytest.mark.asyncio
    async def test_persists_history_on_success(self, tmp_path: Path) -> None:
        """History file is written after successful execution."""
        history = CommandHistory()
        invoker = _make_invoker(history)
        ctx = _make_context(workspace=tmp_path)

        await invoker.execute(_StubCommand(), ctx)

        history_file = tmp_path / "command-history.json"
        assert history_file.exists()


class TestPipelineInvokerExceptionHandling:
    """Verify exception recording and re-raise behavior."""

    @pytest.mark.asyncio
    async def test_re_raises_exception(self) -> None:
        """Exception from command is re-raised after recording."""
        cmd = _StubCommand(_error=ValueError("boom"))
        invoker = _make_invoker()
        ctx = _make_context()

        with pytest.raises(ValueError, match="boom"):
            await invoker.execute(cmd, ctx)

    @pytest.mark.asyncio
    async def test_records_failed_status_on_exception(self) -> None:
        """Exception is recorded as status='failed' with error message."""
        history = CommandHistory()
        cmd = _StubCommand(_name="bad-cmd", _error=RuntimeError("crash"))
        invoker = _make_invoker(history)
        ctx = _make_context()

        with pytest.raises(RuntimeError):
            await invoker.execute(cmd, ctx)

        records = history.all()
        assert len(records) == 1
        assert records[0].name == "bad-cmd"
        assert records[0].status == "failed"
        assert records[0].error == "crash"

    @pytest.mark.asyncio
    async def test_persists_history_on_failure(self, tmp_path: Path) -> None:
        """History is persisted even when the command raises."""
        history = CommandHistory()
        cmd = _StubCommand(_error=OSError("disk"))
        invoker = _make_invoker(history)
        ctx = _make_context(workspace=tmp_path)

        with pytest.raises(OSError):
            await invoker.execute(cmd, ctx)

        history_file = tmp_path / "command-history.json"
        assert history_file.exists()

    @pytest.mark.asyncio
    async def test_persists_when_workspace_is_none(self) -> None:
        """Persistence skips gracefully when workspace is None (no crash)."""
        history = CommandHistory()
        cmd = _StubCommand(_error=ValueError("oops"))
        invoker = _make_invoker(history)
        ctx = _make_context(workspace=None)

        with pytest.raises(ValueError):
            await invoker.execute(cmd, ctx)

        # Should still have the record in memory
        assert len(history) == 1


class TestPipelineInvokerMultipleCommands:
    """Verify history accumulates across multiple command executions."""

    @pytest.mark.asyncio
    async def test_multiple_commands_accumulate(self) -> None:
        """Running multiple commands appends all records."""
        history = CommandHistory()
        invoker = _make_invoker(history)
        ctx = _make_context()

        await invoker.execute(_StubCommand(_name="cmd-1"), ctx)
        await invoker.execute(_StubCommand(_name="cmd-2"), ctx)

        with pytest.raises(RuntimeError):
            await invoker.execute(_StubCommand(_name="cmd-3", _error=RuntimeError("fail")), ctx)

        records = history.all()
        assert len(records) == 3
        assert records[0].status == "success"
        assert records[1].status == "success"
        assert records[2].status == "failed"
