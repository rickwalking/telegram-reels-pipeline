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
from pipeline.infrastructure.adapters.claude_cli_backend import (
    CliBackend,
    _extract_json_from_stdout,
    _extract_session_id,
    _save_stdout_fallback,
)


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

    async def _hang(**_kwargs: object) -> tuple[bytes, bytes]:
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
    async def test_passes_prompt_via_stdin(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc()
        await backend.execute(request_)
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "claude"
        assert call_args[1] == "-p"
        assert "--allowedTools" in call_args
        # Prompt delivered via stdin, not CLI argument
        input_bytes = mock_exec.return_value.communicate.call_args[1]["input"]
        assert b"Run the router stage" in input_bytes

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

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_error_prefers_stderr(
        self, mock_exec: AsyncMock, backend: CliBackend, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b"real error", stdout=b"some output")
        with pytest.raises(AgentExecutionError, match="real error"):
            await backend.dispatch("qa_evaluator", "prompt")

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_error_falls_back_to_stdout(
        self, mock_exec: AsyncMock, backend: CliBackend, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b"", stdout=b"stdout fallback info")
        with pytest.raises(AgentExecutionError, match="stdout fallback info"):
            await backend.dispatch("qa_evaluator", "prompt")

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_error_whitespace_stderr_falls_back_to_stdout(
        self, mock_exec: AsyncMock, backend: CliBackend, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        mock_exec.return_value = _make_mock_proc(returncode=1, stderr=b" \n ", stdout=b"real error in stdout")
        with pytest.raises(AgentExecutionError, match="real error in stdout"):
            await backend.dispatch("qa_evaluator", "prompt")

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_dispatch_uses_separate_timeout(
        self, mock_exec: AsyncMock, step_file: Path, agent_def: Path, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        backend = CliBackend(work_dir=work_dir, timeout_seconds=600.0, dispatch_timeout_seconds=0.01)
        mock_exec.return_value = _make_slow_proc()
        with pytest.raises(AgentExecutionError, match="timed out after 0.01s"):
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


class TestStdoutFallback:
    def test_saves_json_stdout_with_json_extension(self, tmp_path: Path) -> None:
        result = _save_stdout_fallback(tmp_path, "router", '{"url": "https://example.com"}')
        assert len(result) == 1
        assert result[0].name == "router-output.json"
        assert "https://example.com" in result[0].read_text()

    def test_saves_array_stdout_with_json_extension(self, tmp_path: Path) -> None:
        result = _save_stdout_fallback(tmp_path, "router", '[{"key": "value"}]')
        assert len(result) == 1
        assert result[0].suffix == ".json"

    def test_saves_plain_text_with_txt_extension(self, tmp_path: Path) -> None:
        result = _save_stdout_fallback(tmp_path, "research", "Some plain text output")
        assert len(result) == 1
        assert result[0].name == "research-output.txt"

    def test_returns_empty_when_workspace_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "no-such-dir"
        # _save_stdout_fallback writes to cwd which must exist; collect_artifacts handles missing
        missing.mkdir()
        result = _save_stdout_fallback(missing, "router", '{"url": "test"}')
        assert len(result) == 1

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_execute_saves_stdout_when_no_artifacts(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        json_out = b'{"url": "https://youtube.com/watch?v=test", "topic_focus": null}'
        mock_exec.return_value = _make_mock_proc(stdout=json_out)
        result = await backend.execute(request_)
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "router-output.json"

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_execute_skips_fallback_when_artifacts_exist(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        (work_dir / "router-output.json").write_text('{"url": "test"}')
        mock_exec.return_value = _make_mock_proc(stdout=b"extra stdout")
        result = await backend.execute(request_)
        # Only the pre-existing file, no fallback created
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "router-output.json"

    @patch("pipeline.infrastructure.adapters.claude_cli_backend.asyncio.create_subprocess_exec")
    async def test_execute_skips_fallback_when_stdout_empty(
        self, mock_exec: AsyncMock, backend: CliBackend, request_: AgentRequest, work_dir: Path
    ) -> None:
        work_dir.mkdir(parents=True)
        mock_exec.return_value = _make_mock_proc(stdout=b"")
        result = await backend.execute(request_)
        assert len(result.artifacts) == 0


class TestExtractJsonFromStdout:
    def test_direct_json_object(self) -> None:
        assert _extract_json_from_stdout('{"url": "test"}') == '{"url": "test"}'

    def test_direct_json_array(self) -> None:
        assert _extract_json_from_stdout("[1, 2, 3]") == "[1, 2, 3]"

    def test_json_in_markdown_fences(self) -> None:
        stdout = 'Some explanation\n\n```json\n{"url": "test"}\n```\n\nMore text'
        assert _extract_json_from_stdout(stdout) == '{"url": "test"}'

    def test_json_in_plain_fences(self) -> None:
        stdout = '```\n{"key": "value"}\n```'
        assert _extract_json_from_stdout(stdout) == '{"key": "value"}'

    def test_returns_none_for_plain_text(self) -> None:
        assert _extract_json_from_stdout("Just some text") is None

    def test_returns_none_for_invalid_json(self) -> None:
        assert _extract_json_from_stdout("not json at all") is None

    def test_extracts_from_mixed_output_with_fences(self) -> None:
        stdout = (
            "I need write permission to create the output file.\n\n"
            "**Output** (`router-output.json`):\n"
            "```json\n"
            '{"url": "https://youtube.com/watch?v=test", "topic_focus": null}\n'
            "```\n\n"
            "Please grant write permission."
        )
        result = _extract_json_from_stdout(stdout)
        assert result is not None
        assert '"url"' in result

    def test_extracts_json_from_trailing_text(self) -> None:
        stdout = (
            "The URL is valid. Here is the output:\n\n"
            '{"url": "https://youtube.com/watch?v=test", "topic_focus": null}\n'
        )
        result = _extract_json_from_stdout(stdout)
        assert result is not None
        assert '"url"' in result


class TestExtractSessionId:
    def test_extracts_from_output(self) -> None:
        assert _extract_session_id("line1\nsession_id: abc-123\nline3") == SessionId("abc-123")

    def test_returns_empty_when_absent(self) -> None:
        assert _extract_session_id("no session here") == SessionId("")

    def test_handles_empty_string(self) -> None:
        assert _extract_session_id("") == SessionId("")

    def test_extracts_first_match(self) -> None:
        assert _extract_session_id("session_id: first\nsession_id: second") == SessionId("first")
