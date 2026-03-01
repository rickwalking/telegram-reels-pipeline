"""Tests for RunPipelineCommand — orchestration, early exit, stage failures."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from unittest.mock import MagicMock

import pytest

from pipeline.application.cli.commands.run_pipeline import RunPipelineCommand
from pipeline.application.cli.context import PipelineContext
from pipeline.application.cli.history import CommandHistory
from pipeline.application.cli.invoker import PipelineInvoker
from pipeline.application.cli.protocols import CommandResult

# --- Helpers ---


@dataclass
class _StubCommand:
    """Stub command returning a configurable result."""

    _name: str = "stub"
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


def _ok() -> CommandResult:
    return CommandResult(success=True, message="ok")


def _fail(msg: str = "bad") -> CommandResult:
    return CommandResult(success=False, message=msg)


def _exit_early() -> CommandResult:
    return CommandResult(success=True, message="done", data=MappingProxyType({"exit_early": True}))


def _make_context(**overrides: object) -> PipelineContext:
    defaults: dict[str, object] = {
        "settings": MagicMock(),
        "stage_runner": MagicMock(),
        "event_bus": MagicMock(),
    }
    defaults.update(overrides)
    ctx = PipelineContext(**defaults)  # type: ignore[arg-type]
    ctx.state["args"] = MagicMock()
    ctx.state["stages"] = 7
    ctx.state["start_stage"] = 1
    return ctx


def _make_pipeline(
    validate: CommandResult | None = None,
    setup: CommandResult | None = None,
    download: CommandResult | None = None,
) -> RunPipelineCommand:
    history = CommandHistory()
    invoker = PipelineInvoker(history=history)
    return RunPipelineCommand(
        invoker=invoker,
        validate_cmd=_StubCommand(_name="validate", _result=validate or _ok()),
        setup_cmd=_StubCommand(_name="setup", _result=setup or _ok()),
        download_cmd=_StubCommand(_name="download", _result=download or _ok()),
        elicitation_cmd=_StubCommand(_name="elicitation"),
        stage_cmd=_StubCommand(_name="stage"),
    )


# --- Tests ---


class TestRunPipelineCommandName:
    def test_name(self) -> None:
        cmd = _make_pipeline()
        assert cmd.name == "run-pipeline"


class TestRunPipelineCommandValidation:
    @pytest.mark.asyncio
    async def test_validation_failure_stops_pipeline(self) -> None:
        """Pipeline stops if validation fails."""
        cmd = _make_pipeline(validate=_fail("bad args"))
        ctx = _make_context()
        result = await cmd.execute(ctx)
        assert result.success is False
        assert "bad args" in result.message

    @pytest.mark.asyncio
    async def test_exit_early_returns_immediately(self) -> None:
        """Pipeline returns early when all stages complete."""
        cmd = _make_pipeline(validate=_exit_early())
        ctx = _make_context()
        result = await cmd.execute(ctx)
        assert result.success is True
        assert result.data.get("exit_early") is True


class TestRunPipelineCommandSetup:
    @pytest.mark.asyncio
    async def test_setup_failure_stops_pipeline(self) -> None:
        """Pipeline stops if workspace setup fails."""
        cmd = _make_pipeline(setup=_fail("no workspace"))
        ctx = _make_context()
        result = await cmd.execute(ctx)
        assert result.success is False
        assert "no workspace" in result.message


class TestRunPipelineCommandDownload:
    @pytest.mark.asyncio
    async def test_download_failure_stops_pipeline(self) -> None:
        """Pipeline stops if cutaway download fails."""
        cmd = _make_pipeline(download=_fail("download error"))
        ctx = _make_context()
        result = await cmd.execute(ctx)
        assert result.success is False
        assert "download error" in result.message


class TestRunPipelineCommandHappyPath:
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, tmp_path: object) -> None:
        """Full pipeline runs validate → setup → download → stages."""
        cmd = _make_pipeline()
        ctx = _make_context()
        ctx.state["stages"] = 0  # Skip all stages for fast test
        result = await cmd.execute(ctx)
        assert result.success is True
        assert "completed" in result.message.lower()
