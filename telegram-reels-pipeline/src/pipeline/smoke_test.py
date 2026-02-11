"""Smoke test — validate real service connectivity and optionally run a single pipeline.

Usage::

    poetry run python -m pipeline.smoke_test          # connectivity checks only
    poetry run python -m pipeline.smoke_test --run     # checks + single pipeline run
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass

from pipeline.app.settings import PipelineSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Timeout for each service check
_CHECK_TIMEOUT: float = 15.0


@dataclass(frozen=True)
class CheckResult:
    """Result of a single service connectivity check."""

    service: str
    passed: bool
    message: str


# ---------------------------------------------------------------------------
# Service checks
# ---------------------------------------------------------------------------


async def check_telegram(token: str, chat_id: str) -> CheckResult:
    """Send a test message via Telegram Bot API and verify delivery."""
    if not token or not chat_id:
        return CheckResult(service="Telegram", passed=False, message="TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not set")

    try:
        from telegram import Bot

        bot = Bot(token=token)
        async with asyncio.timeout(_CHECK_TIMEOUT):
            await bot.send_message(chat_id=int(chat_id), text="Smoke test: pipeline connectivity check passed.")
        return CheckResult(service="Telegram", passed=True, message="Test message sent successfully")
    except Exception as exc:
        return CheckResult(service="Telegram", passed=False, message=str(exc))


async def check_claude_cli() -> CheckResult:
    """Run ``claude --version`` and verify exit code 0."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(_CHECK_TIMEOUT):
            stdout_bytes, _ = await proc.communicate()

        if proc.returncode != 0:
            return CheckResult(service="Claude CLI", passed=False, message=f"Exit code {proc.returncode}")

        version = stdout_bytes.decode(errors="replace").strip() if stdout_bytes else "unknown"
        return CheckResult(service="Claude CLI", passed=True, message=f"Version: {version}")
    except FileNotFoundError:
        return CheckResult(service="Claude CLI", passed=False, message="'claude' not found in PATH")
    except TimeoutError:
        return CheckResult(service="Claude CLI", passed=False, message=f"Timed out after {_CHECK_TIMEOUT}s")
    except Exception as exc:
        return CheckResult(service="Claude CLI", passed=False, message=str(exc))


async def check_youtube() -> CheckResult:
    """Download metadata for a known public video via yt-dlp."""
    # Short, stable, public video for testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" — first YouTube video
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--dump-json",
            "--no-download",
            test_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(_CHECK_TIMEOUT):
            stdout_bytes, stderr_bytes = await proc.communicate()

        if proc.returncode != 0:
            stderr = stderr_bytes.decode(errors="replace") if stderr_bytes else ""
            msg = f"Exit code {proc.returncode}: {stderr[:200]}"
            return CheckResult(service="YouTube (yt-dlp)", passed=False, message=msg)

        import json

        data = json.loads(stdout_bytes.decode(errors="replace"))
        title = data.get("title", "unknown")
        duration = data.get("duration", 0)
        return CheckResult(
            service="YouTube (yt-dlp)",
            passed=True,
            message=f"Fetched metadata: '{title}' ({duration}s)",
        )
    except FileNotFoundError:
        return CheckResult(service="YouTube (yt-dlp)", passed=False, message="'yt-dlp' not found in PATH")
    except TimeoutError:
        return CheckResult(service="YouTube (yt-dlp)", passed=False, message=f"Timed out after {_CHECK_TIMEOUT}s")
    except Exception as exc:
        return CheckResult(service="YouTube (yt-dlp)", passed=False, message=str(exc))


async def check_ffmpeg() -> CheckResult:
    """Verify ffmpeg is installed and accessible."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        async with asyncio.timeout(_CHECK_TIMEOUT):
            stdout_bytes, _ = await proc.communicate()

        if proc.returncode != 0:
            return CheckResult(service="FFmpeg", passed=False, message=f"Exit code {proc.returncode}")

        first_line = stdout_bytes.decode(errors="replace").split("\n")[0] if stdout_bytes else "unknown"
        return CheckResult(service="FFmpeg", passed=True, message=first_line.strip())
    except FileNotFoundError:
        return CheckResult(service="FFmpeg", passed=False, message="'ffmpeg' not found in PATH")
    except TimeoutError:
        return CheckResult(service="FFmpeg", passed=False, message=f"Timed out after {_CHECK_TIMEOUT}s")
    except Exception as exc:
        return CheckResult(service="FFmpeg", passed=False, message=str(exc))


# ---------------------------------------------------------------------------
# Pipeline run
# ---------------------------------------------------------------------------


async def run_single_pipeline(settings: PipelineSettings) -> CheckResult:
    """Bootstrap the full orchestrator and run a single known-good URL through the pipeline."""
    from datetime import UTC, datetime

    from pipeline.app.bootstrap import create_orchestrator
    from pipeline.domain.models import QueueItem

    try:
        orchestrator = create_orchestrator(settings)
        orchestrator.queue_consumer.ensure_dirs()

        if orchestrator.pipeline_runner is None:
            return CheckResult(service="Pipeline Run", passed=False, message="PipelineRunner not configured")

        # Use a short, known public podcast clip
        test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" — 19s
        item = QueueItem(url=test_url, telegram_update_id=0, queued_at=datetime.now(UTC))

        async with orchestrator.workspace_manager.managed_workspace() as workspace:
            logger.info("Smoke test workspace: %s", workspace)
            state = await orchestrator.pipeline_runner.run(item, workspace)

        return CheckResult(
            service="Pipeline Run",
            passed=state.current_stage.value == "completed",
            message=f"Final stage: {state.current_stage.value}, QA: {state.qa_status.value}",
        )
    except Exception as exc:
        return CheckResult(service="Pipeline Run", passed=False, message=str(exc)[:300])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _print_result(result: CheckResult) -> None:
    """Print a single check result with pass/fail indicator."""
    icon = "PASS" if result.passed else "FAIL"
    print(f"  [{icon}] {result.service}: {result.message}")


async def run_smoke_test(include_pipeline: bool = False) -> bool:
    """Run all connectivity checks and optionally a single pipeline execution.

    Returns True if all critical checks pass.
    """
    settings = PipelineSettings()

    print("\n=== Smoke Test: Service Connectivity ===\n")

    results: list[CheckResult] = []

    # Run connectivity checks concurrently
    checks = await asyncio.gather(
        check_telegram(settings.telegram_token, settings.telegram_chat_id),
        check_claude_cli(),
        check_youtube(),
        check_ffmpeg(),
    )
    results.extend(checks)

    for r in results:
        _print_result(r)

    # Critical services: Claude CLI and yt-dlp must pass
    critical_services = {"Claude CLI", "YouTube (yt-dlp)"}
    critical_failed = [r for r in results if r.service in critical_services and not r.passed]

    if critical_failed:
        print(f"\n  BLOCKED: {len(critical_failed)} critical service(s) failed — skipping pipeline run.")
        return False

    all_passed = all(r.passed for r in results)

    if include_pipeline:
        print("\n=== Smoke Test: Single Pipeline Run ===\n")
        pipeline_result = await run_single_pipeline(settings)
        _print_result(pipeline_result)
        results.append(pipeline_result)
        all_passed = all_passed and pipeline_result.passed

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    print(f"\n=== Results: {passed_count}/{total_count} passed ===\n")

    return all_passed


def main() -> None:
    """Entry point for ``python -m pipeline.smoke_test``."""
    include_pipeline = "--run" in sys.argv
    success = asyncio.run(run_smoke_test(include_pipeline=include_pipeline))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
