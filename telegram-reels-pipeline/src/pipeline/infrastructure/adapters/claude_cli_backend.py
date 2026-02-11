"""CliBackend — Claude Code CLI subprocess execution for agent tasks."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pipeline.application.prompt_builder import build_agent_prompt
from pipeline.domain.errors import AgentExecutionError
from pipeline.domain.models import AgentRequest, AgentResult
from pipeline.domain.types import SessionId
from pipeline.infrastructure.adapters.artifact_collector import collect_artifacts

if TYPE_CHECKING:
    from pipeline.domain.ports import AgentExecutionPort, ModelDispatchPort

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS: float = 300.0


class CliBackend:
    """Execute BMAD agents via ``claude -p`` subprocess.

    Satisfies both AgentExecutionPort and ModelDispatchPort protocols.
    """

    if TYPE_CHECKING:
        _agent_check: AgentExecutionPort
        _model_check: ModelDispatchPort

    def __init__(
        self,
        work_dir: Path,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._work_dir = work_dir
        self._timeout_seconds = timeout_seconds

    async def execute(self, request: AgentRequest) -> AgentResult:
        """Run a Claude Code CLI subprocess and collect results.

        Raises AgentExecutionError on non-zero exit, timeout, or OS errors.
        """
        start = time.monotonic()

        try:
            prompt = build_agent_prompt(request)
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._work_dir),
            )
            async with asyncio.timeout(self._timeout_seconds):
                stdout_bytes, stderr_bytes = await proc.communicate()
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AgentExecutionError(f"Agent {request.stage.value} timed out after {self._timeout_seconds}s") from exc
        except FileNotFoundError as exc:
            raise AgentExecutionError(f"Agent {request.stage.value} failed to prepare prompt: {exc}") from exc
        except OSError as exc:
            raise AgentExecutionError(f"Agent {request.stage.value} failed to start: {exc}") from exc

        duration = time.monotonic() - start
        stdout = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
        returncode = proc.returncode if proc.returncode is not None else 0

        if returncode != 0:
            raise AgentExecutionError(f"Agent {request.stage.value} exited with code {returncode}: {stderr}")

        session_id = _extract_session_id(stdout)
        artifacts = collect_artifacts(self._work_dir)

        logger.info(
            "Agent %s completed in %.1fs with %d artifacts",
            request.stage.value,
            duration,
            len(artifacts),
        )

        return AgentResult(
            status="completed",
            artifacts=artifacts,
            session_id=session_id,
            duration_seconds=duration,
        )

    async def dispatch(self, role: str, prompt: str, model: str | None = None) -> str:
        """Send a raw prompt to Claude CLI and return the text response.

        Used for QA evaluation and other non-agent model calls.
        Raises AgentExecutionError on non-zero exit, timeout, or OS errors.
        """
        cmd = ["claude", "-p", prompt]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._work_dir),
            )
            async with asyncio.timeout(self._timeout_seconds):
                stdout_bytes, stderr_bytes = await proc.communicate()
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AgentExecutionError(
                f"Model dispatch ({role}) timed out after {self._timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise AgentExecutionError(f"Model dispatch ({role}) failed to start: {exc}") from exc

        returncode = proc.returncode if proc.returncode is not None else 0
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""

        if returncode != 0:
            raise AgentExecutionError(f"Model dispatch ({role}) exited with code {returncode}: {stderr}")

        stdout = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
        logger.info("Model dispatch (%s) completed", role)
        return stdout


def _extract_session_id(stdout: str) -> SessionId:
    """Extract session ID from Claude CLI output, if present."""
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("session_id:"):
            return SessionId(stripped.split(":", 1)[1].strip())
    return SessionId("")
