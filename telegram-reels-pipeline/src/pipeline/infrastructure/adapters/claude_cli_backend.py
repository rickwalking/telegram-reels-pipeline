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
DEFAULT_DISPATCH_TIMEOUT_SECONDS: float = 120.0

# Tools allowed for agent execution (stages that need bash, file I/O)
AGENT_ALLOWED_TOOLS: tuple[str, ...] = ("Bash", "Read", "Write", "Edit", "Glob", "Grep")


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
        dispatch_timeout_seconds: float = DEFAULT_DISPATCH_TIMEOUT_SECONDS,
    ) -> None:
        self._work_dir = work_dir
        self._timeout_seconds = timeout_seconds
        self._dispatch_timeout_seconds = dispatch_timeout_seconds
        self._workspace_override: Path | None = None

    def set_workspace(self, workspace: Path | None) -> None:
        """Set per-run workspace override. Pass None to clear."""
        self._workspace_override = workspace

    @property
    def effective_work_dir(self) -> Path:
        """Return the workspace override if set, else the default work_dir."""
        return self._workspace_override or self._work_dir

    async def execute(self, request: AgentRequest) -> AgentResult:
        """Run a Claude Code CLI subprocess and collect results.

        Raises AgentExecutionError on non-zero exit, timeout, or OS errors.
        """
        start = time.monotonic()
        cwd = self.effective_work_dir

        try:
            prompt = build_agent_prompt(request)
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--allowedTools",
                *AGENT_ALLOWED_TOOLS,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
            )
            async with asyncio.timeout(self._timeout_seconds):
                stdout_bytes, stderr_bytes = await proc.communicate(input=prompt.encode())
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
            detail = stderr if stderr else stdout[-2000:]
            raise AgentExecutionError(f"Agent {request.stage.value} exited with code {returncode}: {detail}")

        session_id = _extract_session_id(stdout)
        artifacts = collect_artifacts(cwd)

        # Fallback: save stdout to workspace if agent wrote to stdout instead of files
        if not artifacts and stdout.strip():
            artifacts = _save_stdout_fallback(cwd, request.stage.value, stdout)

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
        Uses --tools "" to disable tool loading (QA doesn't need tools),
        --model sonnet for faster evaluation, and --no-session-persistence
        to skip session save overhead.
        Raises AgentExecutionError on non-zero exit, timeout, or OS errors.
        """
        cwd = self.effective_work_dir
        effective_model = model or "sonnet"

        try:
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--tools",
                "",
                "--model",
                effective_model,
                "--no-session-persistence",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
            )
            async with asyncio.timeout(self._dispatch_timeout_seconds):
                stdout_bytes, stderr_bytes = await proc.communicate(input=prompt.encode())
        except TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise AgentExecutionError(
                f"Model dispatch ({role}) timed out after {self._dispatch_timeout_seconds}s"
            ) from exc
        except OSError as exc:
            raise AgentExecutionError(f"Model dispatch ({role}) failed to start: {exc}") from exc

        returncode = proc.returncode if proc.returncode is not None else 0
        stdout = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
        stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""

        if returncode != 0:
            detail = stderr or stdout[-2000:] if stdout else ""
            raise AgentExecutionError(f"Model dispatch ({role}) exited with code {returncode}: {detail}")

        logger.info(
            "Model dispatch (%s) completed: stdout=%d bytes, stderr=%d bytes",
            role,
            len(stdout),
            len(stderr),
        )
        if not stdout.strip():
            logger.warning(
                "Model dispatch (%s) returned empty stdout. stderr: %.500s",
                role,
                stderr,
            )
        return stdout


def _save_stdout_fallback(cwd: Path, stage_name: str, stdout: str) -> tuple[Path, ...]:
    """Save agent stdout to a file when no artifacts were written to disk.

    Attempts to extract clean JSON from the output. Falls back to saving as text.
    Returns the re-collected artifacts after saving.
    """
    content = _extract_json_from_stdout(stdout)
    if content is not None:
        fallback_path = cwd / f"{stage_name}-output.json"
        fallback_path.write_text(content)
    else:
        fallback_path = cwd / f"{stage_name}-output.txt"
        fallback_path.write_text(stdout)
    logger.warning(
        "Agent %s wrote to stdout instead of files — saved to %s",
        stage_name,
        fallback_path.name,
    )
    return collect_artifacts(cwd)


def _extract_json_from_stdout(stdout: str) -> str | None:
    """Extract JSON content from agent stdout, handling markdown fences and mixed text.

    Tries multiple strategies:
    1. Direct JSON (starts with { or [)
    2. JSON inside markdown code fences
    3. Line-by-line scan for JSON objects
    4. First { to matching } using raw_decode

    Returns the extracted JSON string, or None if no valid JSON found.
    """
    import json
    import re

    stripped = stdout.strip()

    # Strategy 1: Direct JSON output
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            pass

    # Strategy 2: JSON inside markdown code fences
    fence_pattern = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
    for match in fence_pattern.finditer(stripped):
        candidate = match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            continue

    # Strategy 3: Find first { and try raw_decode from there
    brace_idx = stripped.find("{")
    if brace_idx >= 0:
        decoder = json.JSONDecoder()
        try:
            obj, _ = decoder.raw_decode(stripped, brace_idx)
            return json.dumps(obj)
        except json.JSONDecodeError:
            pass

    return None


def _extract_session_id(stdout: str) -> SessionId:
    """Extract session ID from Claude CLI output, if present."""
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("session_id:"):
            return SessionId(stripped.split(":", 1)[1].strip())
    return SessionId("")
