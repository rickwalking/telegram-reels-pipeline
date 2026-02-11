"""Tests for CliBackend — Claude Code CLI subprocess execution."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.domain.enums import PipelineStage
from pipeline.domain.errors import AgentExecutionError
from pipeline.domain.models import AgentRequest, AgentResult
from pipeline.domain.ports import AgentExecutionPort, ModelDispatchPort
from pipeline.domain.types import SessionId
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend, _extract_session_id


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


@pytest.fixture
def step_file(tmp_path: Path) -> Path:
    f = tmp_path / "step.md"
    f.write_text("Run the router stage.")
    return f


@pytest.fixture
def agent_def(tmp_path: Path) -> Path:
    f = tmp_path / "agent.md"
    f.write_text("You are the Router Agent.")
    return f


@pytest.fixture
def request_(step_file: Path, agent_def: Path) -> AgentRequest:
    return AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)


@pytest.fixture
def backend(work_dir: Path) -> CliBackend:
    return CliBackend(work_dir=work_dir, timeout_seconds=10.0)


def _make_mock_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> AsyncMock:
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (stdout, stderr)
    mock_proc.returncode = returncode
    mock_proc.kill = AsyncMock()
    mock_proc.wait = AsyncMock()
    return mock_proc


def _make_slow_proc() -> AsyncMock:
    """Create a mock process whose communicate hangs long enough to trigger timeout."""

    async def _hang() -> tuple[bytes, bytes]:
        await asyncio.sleep(10)
        return (b"", b"")

    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(side_effect=_hang)
    mock_proc.kill = AsyncMock()
    mock_proc.wait = AsyncMock()
    return mock_proc


class TestCliBackendSuccess:
    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_returns_agent_result(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(stdout=b"output text")
        result = await backend.execute(request_)
        assert isinstance(result, AgentResult)
        assert result.status == "completed"

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_duration_is_positive(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc()
        result = await backend.execute(request_)
        assert result.duration_seconds >= 0.0

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_passes_prompt_to_cli(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc()
        await backend.execute(request_)
        call_args = mock_exec.call_args
        assert call_args[0][0] == "claude"
        assert call_args[0][1] == "-p"
        assert "Run the router stage" in call_args[0][2]

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_sets_cwd_to_work_dir(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc()
        await backend.execute(request_)
        assert mock_exec.call_args[1]["cwd"] == str(work_dir)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_collects_workspace_artifacts(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        (work_dir / "output.md").write_text("result")
        (work_dir / "data.json").write_text("{}")
        mock_exec.return_value = _make_mock_proc()
        result = await backend.execute(request_)
        assert len(result.artifacts) == 2

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_extracts_session_id_from_output(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(stdout=b"some output\nsession_id: abc-123\nmore output")
        result = await backend.execute(request_)
        assert result.session_id == SessionId("abc-123")

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_empty_session_id_when_not_in_output(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(stdout=b"plain output")
        result = await backend.execute(request_)
        assert result.session_id == SessionId("")


class TestCliBackendFailure:
    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_nonzero_exit_raises(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b"something broke")
        with pytest.raises(AgentExecutionError, match="exited with code 1"):
            await backend.execute(request_)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_nonzero_exit_includes_stderr(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b"detailed error info")
        with pytest.raises(AgentExecutionError, match="detailed error info"):
            await backend.execute(request_)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_os_error_raises_agent_execution_error(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest
    ) -> None:
        mock_exec.side_effect = OSError("claude not found")
        with pytest.raises(AgentExecutionError, match="failed to start"):
            await backend.execute(request_)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_os_error_preserves_cause(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest
    ) -> None:
        mock_exec.side_effect = OSError("not found")
        with pytest.raises(AgentExecutionError) as exc_info:
            await backend.execute(request_)
        assert isinstance(exc_info.value.__cause__, OSError)

    async def test_missing_step_file_raises_agent_execution_error(self, backend: CliBackend, agent_def: Path) -> None:
        missing = Path("/nonexistent/step.md")
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=missing, agent_definition=agent_def)
        with pytest.raises(AgentExecutionError, match="failed to prepare prompt"):
            await backend.execute(request)

    async def test_missing_step_file_preserves_cause(self, backend: CliBackend, agent_def: Path) -> None:
        missing = Path("/nonexistent/step.md")
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=missing, agent_definition=agent_def)
        with pytest.raises(AgentExecutionError) as exc_info:
            await backend.execute(request)
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)


class TestCliBackendTimeout:
    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_timeout_raises_agent_execution_error(
        self, mock_exec: AsyncMock, step_file: Path, agent_def: Path, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        backend = CliBackend(work_dir=work_dir, timeout_seconds=0.01)
        mock_exec.return_value = _make_slow_proc()
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        with pytest.raises(AgentExecutionError, match="timed out"):
            await backend.execute(request)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_timeout_preserves_cause(
        self, mock_exec: AsyncMock, step_file: Path, agent_def: Path, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        backend = CliBackend(work_dir=work_dir, timeout_seconds=0.01)
        mock_exec.return_value = _make_slow_proc()
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        with pytest.raises(AgentExecutionError) as exc_info:
            await backend.execute(request)
        assert isinstance(exc_info.value.__cause__, TimeoutError)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_timeout_kills_process(
        self, mock_exec: AsyncMock, step_file: Path, agent_def: Path, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        backend = CliBackend(work_dir=work_dir, timeout_seconds=0.01)
        mock_proc = _make_slow_proc()
        mock_exec.return_value = mock_proc
        request = AgentRequest(stage=PipelineStage.ROUTER, step_file=step_file, agent_definition=agent_def)
        with pytest.raises(AgentExecutionError):
            await backend.execute(request)
        mock_proc.kill.assert_called_once()


class TestCliBackendDispatch:
    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_returns_stdout(self, mock_exec: AsyncMock, backend: CliBackend, work_dir: Path) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(stdout=b'{"decision":"PASS","score":85}')
        result = await backend.dispatch("qa_evaluator", "Evaluate this")
        assert '"decision":"PASS"' in result

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_nonzero_exit_raises(
        self, mock_exec: AsyncMock, backend: CliBackend, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b"model error")
        with pytest.raises(AgentExecutionError, match="Model dispatch"):
            await backend.dispatch("qa_evaluator", "Evaluate this")

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_os_error_raises(self, mock_exec: AsyncMock, backend: CliBackend) -> None:
        mock_exec.side_effect = OSError("not found")
        with pytest.raises(AgentExecutionError, match="failed to start"):
            await backend.dispatch("qa_evaluator", "prompt")


class TestCliBackendProtocol:
    def test_satisfies_agent_execution_port(self, backend: CliBackend) -> None:
        assert isinstance(backend, AgentExecutionPort)

    def test_satisfies_model_dispatch_port(self, backend: CliBackend) -> None:
        assert isinstance(backend, ModelDispatchPort)


class TestCliBackendWorkspaceOverride:
    def test_effective_work_dir_defaults_to_work_dir(self, backend: CliBackend, work_dir: Path) -> None:
        assert backend.effective_work_dir == work_dir

    def test_set_workspace_overrides(self, backend: CliBackend, tmp_path: Path) -> None:
        override = tmp_path / "override"
        backend.set_workspace(override)
        assert backend.effective_work_dir == override

    def test_set_workspace_none_clears_override(self, backend: CliBackend, work_dir: Path, tmp_path: Path) -> None:
        backend.set_workspace(tmp_path / "override")
        backend.set_workspace(None)
        assert backend.effective_work_dir == work_dir

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_execute_uses_overridden_workspace(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, tmp_path: Path
    ) -> None:
        override = tmp_path / "run-workspace"
        override.mkdir(parents=True)
        backend.set_workspace(override)
        mock_exec.return_value = _make_mock_proc()
        await backend.execute(request_)
        assert mock_exec.call_args[1]["cwd"] == str(override)

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_uses_overridden_workspace(
        self, mock_exec: AsyncMock, backend: CliBackend, tmp_path: Path
    ) -> None:
        override = tmp_path / "run-workspace"
        override.mkdir(parents=True)
        backend.set_workspace(override)
        mock_exec.return_value = _make_mock_proc(stdout=b"response")
        await backend.dispatch("qa", "prompt")
        assert mock_exec.call_args[1]["cwd"] == str(override)


class TestExtractSessionId:
    def test_extracts_from_output(self) -> None:
        assert _extract_session_id("line1\nsession_id: abc-123\nline3") == SessionId("abc-123")

    def test_returns_empty_when_absent(self) -> None:
        assert _extract_session_id("no session here") == SessionId("")

    def test_handles_empty_string(self) -> None:
        assert _extract_session_id("") == SessionId("")

    def test_extracts_first_match(self) -> None:
        assert _extract_session_id("session_id: first\nsession_id: second") == SessionId("first")
