"""Tests for Veo3 await gate -- polling, timeout, and no-op scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

from pipeline.application.veo3_await_gate import run_veo3_await_gate
from pipeline.application.veo3_orchestrator import Veo3Orchestrator
from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt
from pipeline.infrastructure.adapters.gemini_veo3_adapter import FakeVeo3Adapter


def _write_jobs_json(workspace: Path, jobs: list[dict[str, Any]]) -> None:
    """Write a veo3/jobs.json file with the given job entries."""
    veo3_dir = workspace / "veo3"
    veo3_dir.mkdir(parents=True, exist_ok=True)
    (veo3_dir / "jobs.json").write_text(json.dumps({"jobs": jobs}))


def _make_job_entry(
    variant: str = "broll",
    status: str = "completed",
    key: str = "run1_broll",
) -> dict[str, Any]:
    """Create a single job entry dict for jobs.json."""
    return {
        "idempotent_key": key,
        "variant": variant,
        "prompt": "Test prompt",
        "status": status,
        "video_path": f"veo3/{variant}.mp4" if status == "completed" else None,
        "error_message": None,
    }


class TestNoOpScenarios:
    async def test_no_veo3_folder_returns_skipped(self, tmp_path: Path) -> None:
        """No veo3/ folder -> immediate no-op."""
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=None,
            timeout_s=10,
        )
        assert result["skipped"] is True
        assert result["reason"] == "no_veo3_folder"

    async def test_no_jobs_file_returns_skipped(self, tmp_path: Path) -> None:
        """veo3/ exists but no jobs.json -> no-op."""
        (tmp_path / "veo3").mkdir()
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=None,
            timeout_s=10,
        )
        assert result["skipped"] is True
        assert result["reason"] == "no_jobs_file"


class TestAlreadyCompleted:
    async def test_all_jobs_completed_returns_immediately(self, tmp_path: Path) -> None:
        """All jobs already COMPLETED -> gate returns immediately."""
        _write_jobs_json(
            tmp_path,
            [
                _make_job_entry(variant="broll", status="completed", key="run1_broll"),
                _make_job_entry(variant="intro", status="completed", key="run1_intro"),
            ],
        )

        fake = FakeVeo3Adapter()
        orch = Veo3Orchestrator(video_gen=fake, clip_count=4, timeout_s=300)

        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=10,
        )
        assert result["completed"] == 2
        assert result["total"] == 2
        assert result.get("skipped") is None

    async def test_no_orchestrator_reads_current_state(self, tmp_path: Path) -> None:
        """With no orchestrator, gate reads jobs.json state directly."""
        _write_jobs_json(
            tmp_path,
            [
                _make_job_entry(variant="broll", status="completed", key="run1_broll"),
                _make_job_entry(variant="intro", status="failed", key="run1_intro"),
            ],
        )

        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=None,
            timeout_s=10,
        )
        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


class TestPollingResolvesJobs:
    async def test_polling_resolves_to_completed(self, tmp_path: Path) -> None:
        """Polling converts GENERATING jobs to COMPLETED."""
        fake = FakeVeo3Adapter()

        # Set up orchestrator and generate jobs
        orch = Veo3Orchestrator(video_gen=fake, clip_count=4, timeout_s=300)

        # Write publishing-assets.json for start_generation
        assets = {
            "descriptions": [{"language": "en", "text": "Test"}],
            "hashtags": ["#test"],
            "veo3_prompts": [{"variant": "broll", "prompt": "Abstract particles"}],
        }
        (tmp_path / "publishing-assets.json").write_text(json.dumps(assets))

        await orch.start_generation(tmp_path, "run-await-1")

        # jobs.json should now have GENERATING jobs
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        assert data["jobs"][0]["status"] == "generating"

        # Run the await gate -- FakeVeo3Adapter always returns COMPLETED on poll
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=60,
        )
        assert result["completed"] == 1
        assert result["total"] == 1

    async def test_partial_failure_in_summary(self, tmp_path: Path) -> None:
        """Some jobs fail, others succeed -- summary reflects both."""
        _write_jobs_json(
            tmp_path,
            [
                _make_job_entry(variant="broll", status="completed", key="run1_broll"),
                _make_job_entry(variant="intro", status="failed", key="run1_intro"),
            ],
        )

        fake = FakeVeo3Adapter()
        orch = Veo3Orchestrator(video_gen=fake, clip_count=4, timeout_s=300)

        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=10,
        )
        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


class TestTimeout:
    async def test_timeout_marks_generating_as_timed_out(self, tmp_path: Path) -> None:
        """When timeout exceeded, remaining GENERATING jobs are marked TIMED_OUT."""
        _write_jobs_json(
            tmp_path,
            [
                _make_job_entry(variant="broll", status="generating", key="run1_broll"),
            ],
        )

        # Create an adapter that always returns GENERATING
        class AlwaysGeneratingAdapter:
            def __init__(self) -> None:
                self.submitted_jobs: list[Veo3Job] = []

            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                job = Veo3Job(
                    idempotent_key=prompt.idempotent_key,
                    variant=prompt.variant,
                    prompt=prompt.prompt,
                    status=Veo3JobStatus.GENERATING,
                )
                self.submitted_jobs.append(job)
                return job

            async def poll_job(self, idempotent_key: str) -> Veo3Job:
                return Veo3Job(
                    idempotent_key=idempotent_key,
                    variant="broll",
                    prompt="Test prompt",
                    status=Veo3JobStatus.GENERATING,
                )

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                return dest

        adapter = AlwaysGeneratingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]

        # Use a very short timeout so the test doesn't block
        result = await run_veo3_await_gate(
            workspace=tmp_path,
            orchestrator=orch,
            timeout_s=1,  # 1 second -- first poll at 5s will exceed
        )
        assert result["timed_out"] == 1
        assert result["total"] == 1

        # Verify jobs.json was updated
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        assert data["jobs"][0]["status"] == "timed_out"


class TestBackgroundTaskAwaited:
    async def test_pipeline_runner_awaits_veo3_task_before_gate(self, tmp_path: Path) -> None:
        """PipelineRunner._run_veo3_await_gate awaits self._veo3_task first."""
        from datetime import datetime
        from unittest.mock import MagicMock

        from pipeline.application.pipeline_runner import PipelineRunner
        from pipeline.domain.enums import PipelineStage, QADecision
        from pipeline.domain.models import QACritique, QueueItem, ReflectionResult
        from pipeline.domain.types import GateName

        def _make_result() -> ReflectionResult:
            return ReflectionResult(
                best_critique=QACritique(
                    decision=QADecision.PASS,
                    score=90,
                    gate=GateName("test"),
                    attempt=1,
                    confidence=0.95,
                ),
                artifacts=(),
                attempts=1,
            )

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=_make_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            veo3_adapter=None,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()

        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=1,
            queued_at=datetime(2025, 1, 1),
        )
        result = await runner.run(item, workspace)

        # Pipeline should complete even with VEO3_AWAIT stage (no-op: no veo3/ folder)
        assert result.current_stage == PipelineStage.COMPLETED
