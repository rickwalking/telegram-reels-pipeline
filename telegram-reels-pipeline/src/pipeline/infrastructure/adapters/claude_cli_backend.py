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
DEFAULT_DISPATCH_TIMEOUT_SECONDS: float = 300.0

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
        verbose: bool = False,
        qa_via_clink: bool = False,
    ) -> None:
        self._work_dir = work_dir
        self._timeout_seconds = timeout_seconds
        self._dispatch_timeout_seconds = dispatch_timeout_seconds
        self._workspace_override: Path | None = None
        self._verbose = verbose
        self._qa_via_clink = qa_via_clink

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
            detail = stderr.strip() if stderr and stderr.strip() else stdout[-2000:]
            raise AgentExecutionError(f"Agent {request.stage.value} exited with code {returncode}: {detail}")

        if self._verbose and stdout.strip():
            print(f"\n--- Agent [{request.stage.value}] output ---")
            print(stdout)
            print(f"--- End [{request.stage.value}] output ---\n")

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

        When ``qa_via_clink`` is enabled, uses Claude Haiku as a thin proxy
        that forwards the evaluation to Gemini Pro via the PAL MCP ``clink``
        tool.  This dramatically reduces Claude token usage since Haiku only
        handles the routing while Gemini does the heavy evaluation.

        Raises AgentExecutionError on non-zero exit, timeout, or OS errors.
        """
        cwd = self.effective_work_dir

        if self._qa_via_clink:
            stdout = await self._dispatch_via_clink(role, prompt, cwd)
            # Fallback: if clink returned no valid JSON (Gemini down, rate-limited, etc.),
            # retry with Claude Sonnet directly.
            if stdout is not None and "{" in stdout:
                return stdout
            logger.warning("Clink dispatch returned no JSON — falling back to Claude Sonnet")
            if self._verbose:
                print("  [QA] Clink/Gemini failed — falling back to Claude Sonnet")

        return await self._dispatch_direct(role, prompt, cwd, model or "sonnet")

    async def _dispatch_direct(
        self, role: str, prompt: str, cwd: Path, effective_model: str
    ) -> str:
        """Dispatch via Claude CLI directly (no clink)."""
        cli_args = [
            "claude", "-p",
            "--tools", "",
            "--model", effective_model,
            "--no-session-persistence",
        ]
        return await self._run_dispatch(role, cli_args, prompt, cwd)

    async def _dispatch_via_clink(self, role: str, prompt: str, cwd: Path) -> str | None:
        """Dispatch via clink to Gemini. Returns None on failure."""
        cli_args, wrapped = self._build_clink_dispatch(prompt)
        try:
            return await self._run_dispatch(role, cli_args, wrapped, cwd)
        except AgentExecutionError:
            logger.warning("Clink dispatch failed for %s", role, exc_info=True)
            return None

    async def _run_dispatch(
        self, role: str, cli_args: list[str], prompt: str, cwd: Path
    ) -> str:
        """Run a dispatch subprocess and return stdout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cli_args,
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
            detail = stderr.strip() if stderr and stderr.strip() else stdout[-2000:]
            raise AgentExecutionError(f"Model dispatch ({role}) exited with code {returncode}: {detail}")

        if self._verbose and stdout.strip():
            print(f"\n--- QA [{role}] output ---")
            print(stdout)
            print(f"--- End QA [{role}] output ---\n")

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

    @staticmethod
    def _build_clink_dispatch(prompt: str) -> tuple[list[str], str]:
        """Build CLI args and wrapped prompt for clink-based QA dispatch.

        Uses Claude Haiku as a thin proxy that forwards the evaluation to
        Gemini Pro via PAL MCP's ``clink`` tool.  Haiku only handles the
        tool routing — the actual evaluation work is done by Gemini.
        """
        cli_args = [
            "claude", "-p",
            "--allowedTools", "mcp__pal__clink",
            "--model", "haiku",
            "--no-session-persistence",
        ]
        wrapped = (
            "You are a QA evaluation proxy. Your ONLY job is to forward the "
            "evaluation below to Gemini via the mcp__pal__clink tool and return "
            "its response.\n\n"
            "Call mcp__pal__clink with:\n"
            '- cli_name: "gemini"\n'
            '- prompt: the FULL evaluation text below (copy it exactly)\n\n'
            "Return ONLY the raw text response from Gemini. Do not add any "
            "commentary, formatting, or wrapper text.\n\n"
            "--- EVALUATION TO FORWARD ---\n\n"
            f"{prompt}"
        )
        return cli_args, wrapped


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
