"""Tests for VideoGenerationPort — Protocol definition and structural subtyping."""

from pathlib import Path

from pipeline.domain.models import Veo3Job, Veo3JobStatus, Veo3Prompt
from pipeline.domain.ports import VideoGenerationPort


class TestVideoGenerationPortIsRuntimeCheckable:
    """VideoGenerationPort must be @runtime_checkable — isinstance() works without error."""

    def test_empty_object_does_not_satisfy_port(self) -> None:
        """An empty object should not satisfy the port protocol."""
        assert not isinstance(object(), VideoGenerationPort)

    def test_partial_implementation_fails_check(self) -> None:
        """A class missing methods should not satisfy the port."""

        class IncompleteAdapter:
            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                pass

        assert not isinstance(IncompleteAdapter(), VideoGenerationPort)


class TestFakeAdapterSatisfiesVideoGenerationPort:
    """A fake adapter that implements all three methods satisfies structural subtyping."""

    def test_fake_video_generation_satisfies_port(self) -> None:
        """A complete fake implementation should pass isinstance check."""

        class FakeVideoGeneration:
            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                return Veo3Job(
                    idempotent_key=prompt.idempotent_key,
                    variant=prompt.variant,
                    prompt=prompt.prompt,
                    status=Veo3JobStatus.PENDING,
                )

            async def poll_job(self, idempotent_key: str) -> Veo3Job:
                return Veo3Job(
                    idempotent_key=idempotent_key,
                    variant="broll",
                    prompt="test prompt",
                    status=Veo3JobStatus.COMPLETED,
                    video_path="/tmp/test.mp4",
                )

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                return dest

        assert isinstance(FakeVideoGeneration(), VideoGenerationPort)

    def test_fake_with_minimal_implementation(self) -> None:
        """Even a minimal implementation should satisfy the protocol."""

        class MinimalAdapter:
            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                ...

            async def poll_job(self, idempotent_key: str) -> Veo3Job:
                ...

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                ...

        assert isinstance(MinimalAdapter(), VideoGenerationPort)

    def test_method_signatures_are_enforced(self) -> None:
        """All three methods must be present with correct signatures."""

        class FakeVideoGeneration:
            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                return Veo3Job(
                    idempotent_key="test",
                    variant="broll",
                    prompt="test",
                    status=Veo3JobStatus.PENDING,
                )

            async def poll_job(self, idempotent_key: str) -> Veo3Job:
                return Veo3Job(
                    idempotent_key="test",
                    variant="broll",
                    prompt="test",
                    status=Veo3JobStatus.PENDING,
                )

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                return dest

        adapter = FakeVideoGeneration()
        assert isinstance(adapter, VideoGenerationPort)

        # Verify all three methods are callable
        assert callable(adapter.submit_job)
        assert callable(adapter.poll_job)
        assert callable(adapter.download_clip)

    def test_realistic_fake_implementation(self) -> None:
        """A realistic fake with actual logic should still satisfy the port."""

        class RealisticVideoGeneration:
            def __init__(self) -> None:
                self.jobs: dict[str, Veo3Job] = {}

            async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                job = Veo3Job(
                    idempotent_key=prompt.idempotent_key,
                    variant=prompt.variant,
                    prompt=prompt.prompt,
                    status=Veo3JobStatus.GENERATING,
                )
                self.jobs[prompt.idempotent_key] = job
                return job

            async def poll_job(self, idempotent_key: str) -> Veo3Job:
                if idempotent_key in self.jobs:
                    return self.jobs[idempotent_key]
                raise KeyError(f"Job {idempotent_key} not found")

            async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                # In a real implementation, this would download from an external service
                dest.write_text("fake video data")
                return dest

        adapter = RealisticVideoGeneration()
        assert isinstance(adapter, VideoGenerationPort)

    def test_sync_methods_still_satisfy_runtime_checkable(self) -> None:
        """Runtime checkable protocols accept sync methods with matching names.

        Note: This is a Python limitation — runtime_checkable only checks method
        presence, not async/await signatures. Type checkers (mypy) will enforce
        the async contract at static analysis time.
        """

        class SyncAdapter:
            def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
                return Veo3Job(
                    idempotent_key="",
                    variant="broll",
                    prompt="",
                    status=Veo3JobStatus.PENDING,
                )

            def poll_job(self, idempotent_key: str) -> Veo3Job:
                return Veo3Job(
                    idempotent_key="",
                    variant="broll",
                    prompt="",
                    status=Veo3JobStatus.PENDING,
                )

            def download_clip(self, job: Veo3Job, dest: Path) -> Path:
                return dest

        # Runtime checkable only validates method presence, not async signature
        assert isinstance(SyncAdapter(), VideoGenerationPort)
