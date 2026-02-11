"""Domain ports — Protocol interfaces for hexagonal architecture boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pipeline.domain.models import (
    AgentRequest,
    AgentResult,
    CropRegion,
    QueueItem,
    RunState,
    SegmentLayout,
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
