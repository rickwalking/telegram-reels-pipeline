"""CLI pipeline runner — thin composition root (no business logic).

Usage::

    poetry run python scripts/run_cli.py [youtube_url] [--message "user message"]
    poetry run python scripts/run_cli.py [youtube_url] [--stages 3]
    poetry run python scripts/run_cli.py [youtube_url] --timeout 600
    poetry run python scripts/run_cli.py [youtube_url] --resume /path/to/workspace --start-stage 6
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.app.settings import PipelineSettings  # noqa: E402
from pipeline.application.cli.commands.download_cutaways import DownloadCutawaysCommand  # noqa: E402
from pipeline.application.cli.commands.run_elicitation import RunElicitationCommand  # noqa: E402
from pipeline.application.cli.commands.run_pipeline import RunPipelineCommand  # noqa: E402
from pipeline.application.cli.commands.run_stage import RunStageCommand  # noqa: E402
from pipeline.application.cli.commands.setup_workspace import SetupWorkspaceCommand  # noqa: E402
from pipeline.application.cli.commands.validate_args import ValidateArgsCommand  # noqa: E402
from pipeline.application.cli.context import PipelineContext  # noqa: E402
from pipeline.application.cli.history import CommandHistory  # noqa: E402
from pipeline.application.cli.hooks.encoding_hook import EncodingPlanHook  # noqa: E402
from pipeline.application.cli.hooks.manifest_hook import ManifestBuildHook  # noqa: E402
from pipeline.application.cli.hooks.veo3_await_hook import Veo3AwaitHook  # noqa: E402
from pipeline.application.cli.hooks.veo3_fire_hook import Veo3FireHook  # noqa: E402
from pipeline.application.cli.invoker import PipelineInvoker  # noqa: E402
from pipeline.application.event_bus import EventBus  # noqa: E402
from pipeline.application.recovery_chain import RecoveryChain  # noqa: E402
from pipeline.application.reflection_loop import ReflectionLoop  # noqa: E402
from pipeline.application.stage_runner import StageRunner  # noqa: E402
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend  # noqa: E402
from pipeline.infrastructure.adapters.ffmpeg_adapter import FFmpegAdapter  # noqa: E402
from pipeline.infrastructure.adapters.ffprobe_adapter import FfprobeAdapter  # noqa: E402
from pipeline.infrastructure.adapters.gemini_veo3_adapter import GeminiVeo3Adapter  # noqa: E402
from pipeline.infrastructure.adapters.stdin_reader import StdinReader  # noqa: E402

DEFAULT_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)


def _build_veo3_adapter(settings: PipelineSettings) -> GeminiVeo3Adapter | None:
    """Construct the Veo3 adapter if a Gemini API key is configured."""
    if not settings.gemini_api_key:
        return None
    return GeminiVeo3Adapter(api_key=settings.gemini_api_key)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Pipeline run (no Telegram delivery)")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="YouTube URL")
    parser.add_argument("--message", "-m", default=None, help="Simulated Telegram message")
    parser.add_argument("--stages", "-s", type=int, default=7, help="Max stages to run (default: 7)")
    parser.add_argument("--timeout", "-t", type=float, default=None, help="Agent timeout in seconds")
    parser.add_argument("--resume", type=Path, default=None, help="Resume from existing workspace path")
    parser.add_argument("--start-stage", type=int, default=None, help="Stage number to start from (1-7)")
    parser.add_argument(
        "--style", default=None, choices=["default", "split", "pip", "auto"], help="Framing style for the reel"
    )
    parser.add_argument(
        "--target-duration",
        type=int,
        default=90,
        help="Target duration in seconds (default: 90, max: 300)",
    )
    parser.add_argument(
        "--moments",
        type=int,
        default=None,
        help="Number of narrative moments (1-5). Auto-computed from target-duration when omitted.",
    )
    parser.add_argument(
        "--instructions",
        type=str,
        default=None,
        help="Additional creative instructions (images, transitions, narrative directives).",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print Claude agent output to terminal")
    parser.add_argument(
        "--cutaway",
        action="append",
        default=None,
        metavar="URL@TIMESTAMP",
        help="External clip URL with insertion timestamp (repeatable, e.g. --cutaway URL@30)",
    )
    return parser


async def _run(args: argparse.Namespace) -> None:
    """Wire dependencies and execute the pipeline."""
    settings = PipelineSettings()
    project_root = Path(__file__).resolve().parent.parent

    effective_timeout = args.timeout or settings.agent_timeout_seconds

    # --- Infrastructure adapters ---
    cli_backend = CliBackend(
        work_dir=project_root,
        timeout_seconds=effective_timeout,
        dispatch_timeout_seconds=max(300.0, effective_timeout / 2),
        verbose=args.verbose,
        qa_via_clink=settings.qa_via_clink,
    )
    veo3_adapter = _build_veo3_adapter(settings)

    # --- Application services ---
    event_bus = EventBus()
    recovery_chain = RecoveryChain(agent_port=cli_backend)
    reflection_loop = ReflectionLoop(
        agent_port=cli_backend,
        model_port=cli_backend,
        min_score_threshold=settings.min_qa_score,
    )
    stage_runner = StageRunner(
        reflection_loop=reflection_loop,
        recovery_chain=recovery_chain,
        event_bus=event_bus,
    )

    # --- Hooks (self-selecting via should_run) ---
    hooks = (
        Veo3FireHook(veo3_adapter=veo3_adapter),
        Veo3AwaitHook(veo3_adapter=veo3_adapter, settings=settings),
        ManifestBuildHook(),
        EncodingPlanHook(ffmpeg_adapter=FFmpegAdapter()),
    )

    # --- Commands (dependency injection) ---
    validate_cmd = ValidateArgsCommand()
    setup_cmd = SetupWorkspaceCommand(workspace_base=project_root / "workspace")
    download_cmd = DownloadCutawaysCommand(
        clip_downloader=None,  # type: ignore[arg-type]  # ExternalClipDownloader wired at import time
        duration_prober=FfprobeAdapter(),
    )
    elicitation_cmd = RunElicitationCommand(input_reader=StdinReader(), stage_runner=stage_runner)
    stage_cmd = RunStageCommand(stage_runner=stage_runner, hooks=hooks)

    history = CommandHistory()
    invoker = PipelineInvoker(history=history)

    pipeline_cmd = RunPipelineCommand(
        invoker=invoker,
        validate_cmd=validate_cmd,
        setup_cmd=setup_cmd,
        download_cmd=download_cmd,
        elicitation_cmd=elicitation_cmd,
        stage_cmd=stage_cmd,
    )

    # --- Context ---
    message = args.message if args.message else args.url
    context = PipelineContext(
        settings=settings,
        stage_runner=stage_runner,
        event_bus=event_bus,
        youtube_url=args.url,
        user_message=message,
        timeout_seconds=effective_timeout,
        resume_workspace=str(args.resume) if args.resume else "",
    )
    context.state["args"] = args
    context.state["cutaway_specs"] = args.cutaway
    context.state["instructions"] = args.instructions
    context.state["cli_backend"] = cli_backend
    context.state["workflows_dir"] = str(project_root / "workflows")
    context.state["agents_dir"] = str(project_root / "agents")

    try:
        result = await invoker.execute(pipeline_cmd, context)
        if not result.success:
            print(f"\nPipeline failed: {result.message}", file=sys.stderr)
            sys.exit(1)
    finally:
        cli_backend.set_workspace(None)


def main() -> None:
    """CLI entry point — parse args and run."""
    parser = _build_arg_parser()
    args = parser.parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
