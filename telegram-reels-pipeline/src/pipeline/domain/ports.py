"""Domain ports — Protocol interfaces for hexagonal architecture boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pipeline.domain.models import (
    AgentRequest,
    AgentResult,
    CropRegion,
    QueueItem,
    ResourceSnapshot,
    RunState,
    SegmentLayout,
    Veo3Job,
    Veo3Prompt,
    VideoMetadata,
)
from pipeline.domain.types import RunId


@runtime_checkable
class AgentExecutionPort(Protocol):
    """Execute a BMAD agent via CLI or SDK backend."""

    async def execute(self, request: AgentRequest) -> AgentResult: ...


@runtime_checkable
class ModelDispatchPort(Protocol):
    """Route prompts to specific AI models for QA or analysis."""

    async def dispatch(self, role: str, prompt: str, model: str | None = None) -> str: ...


@runtime_checkable
class MessagingPort(Protocol):
    """Communicate with the user via Telegram."""

    async def ask_user(self, question: str) -> str: ...

    async def notify_user(self, message: str) -> None: ...

    async def send_file(self, path: Path, caption: str) -> None: ...


@runtime_checkable
class QueuePort(Protocol):
    """Enqueue pipeline requests and inspect queue state."""

    def enqueue(self, item: QueueItem) -> Path: ...

    def pending_count(self) -> int: ...

    def processing_count(self) -> int: ...


@runtime_checkable
class VideoProcessingPort(Protocol):
    """Process video via FFmpeg — frame extraction, crop, encode."""

    async def extract_frames(self, video: Path, timestamps: list[float]) -> list[Path]: ...

    async def crop_and_encode(self, video: Path, segments: list[SegmentLayout], output: Path) -> Path: ...


@runtime_checkable
class VideoDownloadPort(Protocol):
    """Download video content and metadata via yt-dlp."""

    async def download_metadata(self, url: str) -> VideoMetadata: ...

    async def download_subtitles(self, url: str, output: Path) -> Path: ...

    async def download_video(self, url: str, output: Path) -> Path: ...


@runtime_checkable
class StateStorePort(Protocol):
    """Persist and retrieve pipeline run state."""

    async def save_state(self, state: RunState) -> None: ...

    async def load_state(self, run_id: RunId) -> RunState | None: ...

    async def list_incomplete_runs(self) -> list[RunState]: ...


@runtime_checkable
class FileDeliveryPort(Protocol):
    """Upload files to external storage (Google Drive) for large file delivery."""

    async def upload(self, path: Path) -> str: ...


@runtime_checkable
class KnowledgeBasePort(Protocol):
    """CRUD operations on the layout knowledge base (crop-strategies.yaml)."""

    async def get_strategy(self, layout_name: str) -> CropRegion | None: ...

    async def save_strategy(self, layout_name: str, region: CropRegion) -> None: ...

    async def list_strategies(self) -> dict[str, CropRegion]: ...


@runtime_checkable
class ResourceMonitorPort(Protocol):
    """Read system resource metrics (CPU, memory, temperature)."""

    async def snapshot(self) -> ResourceSnapshot: ...


@runtime_checkable
class VideoGenerationPort(Protocol):
    """Generate short video clips via Veo 3 API for B-roll and transitions."""

    async def submit_job(self, prompt: Veo3Prompt) -> Veo3Job:
        """Submit a video generation job with the given prompt.

        Args:
            prompt: Veo3Prompt specifying variant, text, and duration.

        Returns:
            Veo3Job tracking the submitted job with initial GENERATING status.
            The returned job includes ``operation_name`` for later polling
            and authenticated download via the Gemini API.
        """
        ...

    async def poll_job(self, idempotent_key: str) -> Veo3Job:
        """Poll the status of a previously submitted job.

        Args:
            idempotent_key: The idempotent key returned from submit_job.

        Returns:
            Updated Veo3Job with current status and video_path (if completed).
        """
        ...

    async def download_clip(self, job: Veo3Job, dest: Path) -> Path:
        """Download a completed video clip to the specified destination.

        Args:
            job: Veo3Job with status COMPLETED and video_path set.
            dest: Destination Path where the clip should be written.

        Returns:
            Path to the downloaded file (same as dest).
        """
        ...
