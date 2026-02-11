"""Dry run — exercise the first 3 pipeline stages with a real YouTube URL.

Validates: prompt building, Claude CLI subprocess, yt-dlp, QA evaluation,
artifact passing between stages. Skips stages 4-8.

Usage::

    poetry run python scripts/dry_run.py [youtube_url]
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from datetime import UTC, datetime
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
logger = logging.getLogger("dry_run")

# The first 3 stages to exercise
DRY_RUN_STAGES = (
    (PipelineStage.ROUTER, "stage-01-router.md", "router", "router"),
    (PipelineStage.RESEARCH, "stage-02-research.md", "research", "research"),
    (PipelineStage.TRANSCRIPT, "stage-03-transcript.md", "transcript", "transcript"),
)

DEFAULT_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" — 19s


async def run_dry(url: str) -> None:
    settings = PipelineSettings()
    project_root = Path(__file__).resolve().parent.parent

    workflows_dir = project_root / "workflows"
    agents_dir = project_root / "agents"

    cli_backend = CliBackend(
        work_dir=project_root,
        timeout_seconds=settings.agent_timeout_seconds,
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

    print(f"\n{'='*60}")
    print(f"  DRY RUN — First 3 stages")
    print(f"  URL: {url}")
    print(f"{'='*60}\n")

    workspace = workspace_mgr.create_workspace()
    cli_backend.set_workspace(workspace)
    print(f"  Workspace: {workspace}\n")

    artifacts: tuple[Path, ...] = ()
    overall_start = time.monotonic()

    try:
        for stage, step_file_name, agent_dir, gate_name in DRY_RUN_STAGES:
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
                elicitation["youtube_url"] = url

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
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    asyncio.run(run_dry(url))


if __name__ == "__main__":
    main()
