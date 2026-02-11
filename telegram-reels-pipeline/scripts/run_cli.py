"""CLI pipeline runner — run the full pipeline from a terminal (no Telegram).

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
import time
from pathlib import Path
from types import MappingProxyType

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pipeline.app.settings import PipelineSettings
from pipeline.application.event_bus import EventBus
from pipeline.application.recovery_chain import RecoveryChain
from pipeline.application.reflection_loop import ReflectionLoop
from pipeline.application.stage_runner import StageRunner
from pipeline.application.workspace_manager import WorkspaceManager
from pipeline.domain.enums import PipelineStage
from pipeline.domain.models import AgentRequest
from pipeline.domain.types import GateName
from pipeline.infrastructure.adapters.claude_cli_backend import CliBackend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("run_cli")

# All pipeline stages in order (delivery skipped — no Telegram)
ALL_STAGES = (
    (PipelineStage.ROUTER, "stage-01-router.md", "router", "router"),
    (PipelineStage.RESEARCH, "stage-02-research.md", "research", "research"),
    (PipelineStage.TRANSCRIPT, "stage-03-transcript.md", "transcript", "transcript"),
    (PipelineStage.CONTENT, "stage-04-content.md", "content-creator", "content"),
    (PipelineStage.LAYOUT_DETECTIVE, "stage-05-layout-detective.md", "layout-detective", "layout"),
    (PipelineStage.FFMPEG_ENGINEER, "stage-06-ffmpeg-engineer.md", "ffmpeg-engineer", "ffmpeg"),
    (PipelineStage.ASSEMBLY, "stage-07-assembly.md", "qa", "assembly"),
)

DEFAULT_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


async def run_pipeline(
    url: str,
    message: str,
    max_stages: int,
    timeout_seconds: float | None = None,
    resume_workspace: Path | None = None,
    start_stage: int = 1,
) -> None:
    settings = PipelineSettings()
    project_root = Path(__file__).resolve().parent.parent

    workflows_dir = project_root / "workflows"
    agents_dir = project_root / "agents"

    effective_timeout = timeout_seconds or settings.agent_timeout_seconds

    cli_backend = CliBackend(
        work_dir=project_root,
        timeout_seconds=effective_timeout,
    )
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
    workspace_mgr = WorkspaceManager(base_dir=project_root / "workspace")

    stages = ALL_STAGES[:max_stages]

    print(f"\n{'='*60}")
    print(f"  PIPELINE RUN — {len(stages)} stages (starting at stage {start_stage})")
    print(f"  URL: {url}")
    if message != url:
        print(f"  Message: {message}")
    print(f"  Timeout: {effective_timeout}s")
    print(f"{'='*60}\n")

    if resume_workspace and resume_workspace.exists():
        workspace = resume_workspace
        print(f"  Resuming workspace: {workspace}")
    else:
        workspace = workspace_mgr.create_workspace()
        print(f"  New workspace: {workspace}")

    cli_backend.set_workspace(workspace)
    print()

    # Collect existing artifacts from workspace when resuming
    artifacts: tuple[Path, ...] = ()
    if start_stage > 1:
        existing = sorted(p for p in workspace.iterdir() if p.is_file())
        artifacts = tuple(existing)
        print(f"  Loaded {len(artifacts)} existing artifacts from workspace")
        for a in artifacts:
            print(f"    - {a.name}")
        print()

    overall_start = time.monotonic()

    try:
        for stage_idx, (stage, step_file_name, agent_dir, gate_name) in enumerate(stages, 1):
            if stage_idx < start_stage:
                print(f"  [{stage.value.upper()}] Skipped (resuming)")
                continue
            step_file = workflows_dir / "stages" / step_file_name
            agent_def = agents_dir / agent_dir / "agent.md"

            if not step_file.exists():
                print(f"  [SKIP] {stage.value}: step file missing ({step_file})")
                continue
            if not agent_def.exists():
                print(f"  [SKIP] {stage.value}: agent definition missing ({agent_def})")
                continue

            elicitation: dict[str, str] = {}
            if stage == PipelineStage.ROUTER:
                # Ensure the URL is always present in the message (as it would be in a real Telegram message)
                if url not in message:
                    elicitation["telegram_message"] = f"{url} {message}"
                else:
                    elicitation["telegram_message"] = message

            request = AgentRequest(
                stage=stage,
                step_file=step_file,
                agent_definition=agent_def,
                prior_artifacts=artifacts,
                elicitation_context=MappingProxyType(elicitation),
            )

            criteria_path = workflows_dir / "qa" / "gate-criteria" / f"{gate_name}-criteria.md"
            gate_criteria = criteria_path.read_text() if criteria_path.exists() else ""

            print(f"  [{stage.value.upper()}] Starting...")
            stage_start = time.monotonic()

            try:
                result = await stage_runner.run_stage(
                    request,
                    gate=GateName(gate_name),
                    gate_criteria=gate_criteria,
                )
                elapsed = time.monotonic() - stage_start
                artifacts = result.artifacts

                print(f"  [{stage.value.upper()}] Done in {elapsed:.1f}s")
                print(f"    Decision: {result.best_critique.decision.value}")
                print(f"    Score: {result.best_critique.score}")
                print(f"    Attempts: {result.attempts}")
                print(f"    Artifacts: {len(artifacts)}")
                for a in artifacts:
                    print(f"      - {a.name}")

                if result.escalation_needed:
                    print(f"    ESCALATION needed — stopping.")
                    break

            except Exception as exc:
                elapsed = time.monotonic() - stage_start
                print(f"  [{stage.value.upper()}] FAILED after {elapsed:.1f}s")
                print(f"    Error: {exc}")
                break

            print()

    finally:
        cli_backend.set_workspace(None)

    total = time.monotonic() - overall_start
    print(f"\n{'='*60}")
    print(f"  Total time: {total:.1f}s")
    print(f"  Workspace: {workspace}")
    print(f"{'='*60}\n")

    # Show workspace contents
    print("  Workspace contents:")
    for p in sorted(workspace.rglob("*")):
        if p.is_file():
            rel = p.relative_to(workspace)
            size = p.stat().st_size
            print(f"    {rel} ({size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline run (no Telegram delivery)")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="YouTube URL")
    parser.add_argument("--message", "-m", default=None, help="Simulated Telegram message")
    parser.add_argument("--stages", "-s", type=int, default=7, help="Max stages to run (default: 7)")
    parser.add_argument("--timeout", "-t", type=float, default=None, help="Agent timeout in seconds (default: from settings)")
    parser.add_argument("--resume", type=Path, default=None, help="Resume from existing workspace path")
    parser.add_argument("--start-stage", type=int, default=1, help="Stage number to start from (1-7, default: 1)")
    args = parser.parse_args()

    message = args.message if args.message else args.url
    asyncio.run(run_pipeline(args.url, message, args.stages, args.timeout, args.resume, args.start_stage))


if __name__ == "__main__":
    main()
