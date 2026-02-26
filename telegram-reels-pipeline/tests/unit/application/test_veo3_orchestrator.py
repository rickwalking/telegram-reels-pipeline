"""Tests for Veo3Orchestrator — async generation and polling worker."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from pipeline.application.veo3_orchestrator import Veo3Orchestrator
from pipeline.domain.enums import PipelineStage, QADecision
from pipeline.domain.models import (
    QACritique,
    QueueItem,
    ReflectionResult,
    Veo3Job,
    Veo3JobStatus,
    Veo3Prompt,
)
from pipeline.domain.types import GateName
from pipeline.infrastructure.adapters.gemini_veo3_adapter import FakeVeo3Adapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_publishing_assets(workspace: Path, prompts: list[dict[str, object]]) -> None:
    """Write a publishing-assets.json file with the given veo3_prompts."""
    assets = {
        "descriptions": [{"language": "en", "text": "Test description"}],
        "hashtags": ["#test"],
        "veo3_prompts": prompts,
    }
    (workspace / "publishing-assets.json").write_text(json.dumps(assets))


def _prompt_dict(**overrides: Any) -> dict[str, object]:
    defaults: dict[str, object] = {
        "variant": "broll",
        "prompt": "Abstract data visualization with flowing particles",
    }
    defaults.update(overrides)
    return defaults


def _make_orchestrator(
    adapter: FakeVeo3Adapter | None = None,
    clip_count: int = 4,
    timeout_s: int = 300,
) -> tuple[Veo3Orchestrator, FakeVeo3Adapter]:
    fake = adapter or FakeVeo3Adapter()
    orch = Veo3Orchestrator(video_gen=fake, clip_count=clip_count, timeout_s=timeout_s)
    return orch, fake


# ---------------------------------------------------------------------------
# TestStartGeneration
# ---------------------------------------------------------------------------


class TestStartGeneration:
    async def test_valid_prompts_creates_jobs_json(self, tmp_path: Path) -> None:
        """start_generation with valid prompts creates veo3/jobs.json."""
        orch, fake = _make_orchestrator()
        prompts = [_prompt_dict()]
        _write_publishing_assets(tmp_path, prompts)

        await orch.start_generation(tmp_path, "run-001")

        jobs_path = tmp_path / "veo3" / "jobs.json"
        assert jobs_path.exists()
        data = json.loads(jobs_path.read_text())
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["variant"] == "broll"
        assert data["jobs"][0]["status"] == "generating"
        assert len(fake.submitted_jobs) == 1

    async def test_empty_prompts_is_noop(self, tmp_path: Path) -> None:
        """start_generation with empty prompts does nothing."""
        orch, _ = _make_orchestrator()
        _write_publishing_assets(tmp_path, [])

        await orch.start_generation(tmp_path, "run-002")

        assert not (tmp_path / "veo3").exists()

    async def test_missing_assets_file_is_noop(self, tmp_path: Path) -> None:
        """start_generation with no publishing-assets.json is a no-op."""
        orch, _ = _make_orchestrator()

        await orch.start_generation(tmp_path, "run-003")

        assert not (tmp_path / "veo3").exists()

    async def test_prompts_capped_at_clip_count(self, tmp_path: Path) -> None:
        """Only clip_count prompts are submitted even if more are provided."""
        orch, fake = _make_orchestrator(clip_count=2)
        prompts = [
            _prompt_dict(variant="intro", prompt="Dramatic intro sequence"),
            _prompt_dict(variant="broll", prompt="Abstract data visualization"),
            _prompt_dict(variant="outro", prompt="Fade to black ending"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        await orch.start_generation(tmp_path, "run-004")

        # Only 2 submitted despite 3 prompts
        assert len(fake.submitted_jobs) == 2

    async def test_sequential_submission(self, tmp_path: Path) -> None:
        """All prompts are submitted sequentially."""
        orch, fake = _make_orchestrator()
        prompts = [
            _prompt_dict(variant="intro", prompt="Dramatic intro sequence"),
            _prompt_dict(variant="broll", prompt="Abstract data visualization"),
            _prompt_dict(variant="outro", prompt="Fade to black ending"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        await orch.start_generation(tmp_path, "run-005")

        assert len(fake.submitted_jobs) == 3
        variants = {j.variant for j in fake.submitted_jobs}
        assert variants == {"intro", "broll", "outro"}

    async def test_idempotent_keys_follow_pattern(self, tmp_path: Path) -> None:
        """Idempotent keys follow {run_id}_{variant} pattern."""
        orch, fake = _make_orchestrator()
        prompts = [
            _prompt_dict(variant="broll", prompt="Test prompt"),
            _prompt_dict(variant="intro", prompt="Intro prompt"),
        ]
        _write_publishing_assets(tmp_path, prompts)

        await orch.start_generation(tmp_path, "run-006")

        keys = {j.idempotent_key for j in fake.submitted_jobs}
        assert keys == {"run-006_broll", "run-006_intro"}

    async def test_veo3_dir_created(self, tmp_path: Path) -> None:
        """The veo3/ subfolder is created in workspace."""
        orch, _ = _make_orchestrator()
        _write_publishing_assets(tmp_path, [_prompt_dict()])

        await orch.start_generation(tmp_path, "run-007")

        assert (tmp_path / "veo3").is_dir()

    async def test_prompt_with_optional_fields(self, tmp_path: Path) -> None:
        """Prompts with narrative_anchor and duration_s are handled."""
        orch, fake = _make_orchestrator()
        prompts = [
            _prompt_dict(
                variant="broll",
                prompt="Abstract particles",
                narrative_anchor="during the AI discussion",
                duration_s=7,
            )
        ]
        _write_publishing_assets(tmp_path, prompts)

        await orch.start_generation(tmp_path, "run-008")

        assert len(fake.submitted_jobs) == 1

    async def test_jobs_json_includes_prompt_field(self, tmp_path: Path) -> None:
        """jobs.json entries contain the prompt text."""
        orch, _ = _make_orchestrator()
        _write_publishing_assets(tmp_path, [_prompt_dict(prompt="My test prompt")])

        await orch.start_generation(tmp_path, "run-009")

        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        assert data["jobs"][0]["prompt"] == "My test prompt"


# ---------------------------------------------------------------------------
# TestPollJobs
# ---------------------------------------------------------------------------


class TestPollJobs:
    async def test_updates_generating_to_completed(self, tmp_path: Path) -> None:
        """poll_jobs updates GENERATING status to COMPLETED."""
        orch, fake = _make_orchestrator()
        _write_publishing_assets(tmp_path, [_prompt_dict()])

        await orch.start_generation(tmp_path, "run-poll-1")

        # Now poll
        all_done = await orch.poll_jobs(tmp_path)

        assert all_done is True
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        assert data["jobs"][0]["status"] == "completed"

    async def test_partial_failure_others_continue(self, tmp_path: Path) -> None:
        """One job fails on poll, other succeeds."""

        class PartialPollFailAdapter:
            """Adapter that fails poll for intro but succeeds for broll."""

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
                for job in self.submitted_jobs:
                    if job.idempotent_key == idempotent_key:
                        if "intro" in idempotent_key:
                            raise RuntimeError("API error for intro")
                        return Veo3Job(
                            idempotent_key=job.idempotent_key,
                            variant=job.variant,
                            prompt=job.prompt,
                            status=Veo3JobStatus.COMPLETED,
                            video_path=f"veo3/{job.variant}.mp4",
                        )
                raise RuntimeError(f"Unknown key: {idempotent_key}")

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.touch()
                return dest

        adapter = PartialPollFailAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        prompts = [
            _prompt_dict(variant="intro", prompt="Intro sequence"),
            _prompt_dict(variant="broll", prompt="Abstract visualization"),
        ]
        _write_publishing_assets(tmp_path, prompts)
        await orch.start_generation(tmp_path, "run-partial")

        # Poll jobs
        all_done = await orch.poll_jobs(tmp_path)

        assert all_done is True
        data = json.loads((tmp_path / "veo3" / "jobs.json").read_text())
        statuses = {j["variant"]: j["status"] for j in data["jobs"]}
        assert statuses["intro"] == "failed"
        assert statuses["broll"] == "completed"

    async def test_returns_true_when_all_terminal(self, tmp_path: Path) -> None:
        """poll_jobs returns True when all jobs are in terminal state."""
        orch, _ = _make_orchestrator()
        _write_publishing_assets(tmp_path, [_prompt_dict()])
        await orch.start_generation(tmp_path, "run-terminal")

        result = await orch.poll_jobs(tmp_path)

        assert result is True

    async def test_returns_false_when_still_generating(self, tmp_path: Path) -> None:
        """poll_jobs returns False when some jobs are still GENERATING."""

        class AlwaysGeneratingAdapter:
            """Adapter that always returns GENERATING on poll."""

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
                for job in self.submitted_jobs:
                    if job.idempotent_key == idempotent_key:
                        return Veo3Job(
                            idempotent_key=job.idempotent_key,
                            variant=job.variant,
                            prompt=job.prompt,
                            status=Veo3JobStatus.GENERATING,
                        )
                raise RuntimeError(f"Unknown key: {idempotent_key}")

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                return dest

        adapter = AlwaysGeneratingAdapter()
        orch = Veo3Orchestrator(video_gen=adapter, clip_count=4, timeout_s=300)  # type: ignore[arg-type]
        _write_publishing_assets(tmp_path, [_prompt_dict()])
        await orch.start_generation(tmp_path, "run-still")

        result = await orch.poll_jobs(tmp_path)

        assert result is False

    async def test_poll_nonexistent_jobs_json_returns_true(self, tmp_path: Path) -> None:
        """poll_jobs returns True if veo3/jobs.json does not exist."""
        orch, _ = _make_orchestrator()
        result = await orch.poll_jobs(tmp_path)
        assert result is True


# ---------------------------------------------------------------------------
# TestAtomicWrites
# ---------------------------------------------------------------------------


class TestAtomicWrites:
    def test_write_jobs_json_creates_valid_json(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs_path.parent.mkdir(parents=True)
        jobs = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.PENDING,
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs)

        data = json.loads(jobs_path.read_text())
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["idempotent_key"] == "run1_broll"
        assert data["jobs"][0]["prompt"] == "Test"
        assert data["jobs"][0]["status"] == "pending"
        assert data["jobs"][0]["video_path"] is None

    def test_write_jobs_json_overwrites_existing(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs_path.parent.mkdir(parents=True)

        jobs_v1 = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.PENDING,
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs_v1)

        jobs_v2 = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.COMPLETED,
                video_path="veo3/broll.mp4",
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs_v2)

        data = json.loads(jobs_path.read_text())
        assert data["jobs"][0]["status"] == "completed"
        assert data["jobs"][0]["video_path"] == "veo3/broll.mp4"

    def test_no_stale_temp_files_on_success(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "veo3" / "jobs.json"
        jobs_path.parent.mkdir(parents=True)
        jobs = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.PENDING,
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs)

        tmp_files = list(jobs_path.parent.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_write_creates_parent_dirs(self, tmp_path: Path) -> None:
        jobs_path = tmp_path / "deep" / "nested" / "veo3" / "jobs.json"
        jobs = [
            Veo3Job(
                idempotent_key="run1_broll",
                variant="broll",
                prompt="Test",
                status=Veo3JobStatus.PENDING,
            )
        ]
        Veo3Orchestrator._write_jobs_json(jobs_path, jobs)
        assert jobs_path.exists()


# ---------------------------------------------------------------------------
# TestPipelineRunnerHook
# ---------------------------------------------------------------------------


class TestPipelineRunnerHook:
    def _make_reflection_result(self) -> ReflectionResult:
        return ReflectionResult(
            best_critique=QACritique(
                decision=QADecision.PASS,
                score=90,
                gate=GateName("test"),
                attempt=1,
                confidence=0.95,
            ),
            artifacts=(Path("/tmp/artifact.md"),),
            attempts=1,
        )

    async def test_content_stage_fires_veo3_background(self, tmp_path: Path) -> None:
        """After CONTENT stage, a Veo3 background task is created."""
        from pipeline.application.pipeline_runner import PipelineRunner

        fake_adapter = FakeVeo3Adapter()

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=self._make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            veo3_adapter=fake_adapter,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()
        _write_publishing_assets(workspace, [_prompt_dict()])

        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=1,
            queued_at=datetime(2025, 1, 1),
        )
        result = await runner.run(item, workspace)

        assert result.current_stage == PipelineStage.COMPLETED
        # VEO3_AWAIT gate awaits and clears the background task
        assert runner._veo3_task is None
        assert len(fake_adapter.submitted_jobs) == 1

    async def test_no_adapter_does_not_crash(self, tmp_path: Path) -> None:
        """When veo3_adapter is None, pipeline runs normally."""
        from pipeline.application.pipeline_runner import PipelineRunner

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=self._make_reflection_result())),
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
        assert result.current_stage == PipelineStage.COMPLETED
        assert runner._veo3_task is None

    async def test_missing_assets_file_does_not_crash(self, tmp_path: Path) -> None:
        """If publishing-assets.json is missing, Veo3 hook is a no-op."""
        from pipeline.application.pipeline_runner import PipelineRunner

        fake_adapter = FakeVeo3Adapter()

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=self._make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            veo3_adapter=fake_adapter,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()

        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=1,
            queued_at=datetime(2025, 1, 1),
        )
        result = await runner.run(item, workspace)
        assert result.current_stage == PipelineStage.COMPLETED
        if runner._veo3_task is not None:
            await runner._veo3_task
        assert len(fake_adapter.submitted_jobs) == 0

    async def test_veo3_error_does_not_crash_pipeline(self, tmp_path: Path) -> None:
        """If Veo3 generation throws, the pipeline continues."""
        from pipeline.application.pipeline_runner import PipelineRunner

        failing_adapter = FakeVeo3Adapter(fail_on_submit=True)

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=self._make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            veo3_adapter=failing_adapter,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()
        _write_publishing_assets(workspace, [_prompt_dict()])

        item = QueueItem(
            url="https://youtube.com/watch?v=test",
            telegram_update_id=1,
            queued_at=datetime(2025, 1, 1),
        )
        result = await runner.run(item, workspace)
        assert result.current_stage == PipelineStage.COMPLETED

    async def test_resume_fires_veo3_on_content_stage(self, tmp_path: Path) -> None:
        """Resume through CONTENT stage also fires Veo3 hook."""
        from pipeline.application.pipeline_runner import PipelineRunner
        from pipeline.domain.models import RunState
        from pipeline.domain.types import RunId

        fake_adapter = FakeVeo3Adapter()

        runner = PipelineRunner(
            stage_runner=MagicMock(run_stage=AsyncMock(return_value=self._make_reflection_result())),
            state_store=MagicMock(save_state=AsyncMock()),
            event_bus=MagicMock(publish=AsyncMock()),
            delivery_handler=None,
            workflows_dir=Path("/wf"),
            veo3_adapter=fake_adapter,
        )

        workspace = tmp_path / "ws"
        workspace.mkdir()
        _write_publishing_assets(workspace, [_prompt_dict()])

        prior = RunState(
            run_id=RunId("resume-veo3-001"),
            youtube_url="https://youtube.com/watch?v=resume",
            current_stage=PipelineStage.CONTENT,
            stages_completed=("router", "research", "transcript"),
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
        )
        result = await runner.resume(prior, PipelineStage.CONTENT, workspace)
        assert result.current_stage == PipelineStage.COMPLETED
        # VEO3_AWAIT gate awaits and clears the background task
        assert runner._veo3_task is None
        assert len(fake_adapter.submitted_jobs) == 1
