<<<<<<< HEAD
<<<<<<< HEAD
=======
>>>>>>> worktree-agent-adf76045
"""Domain ports package — re-exports all port protocols for backward compatibility."""

from __future__ import annotations

<<<<<<< HEAD
from pipeline.domain.ports.agent_execution_port import AgentExecutionPort
from pipeline.domain.ports.event_store_port import EventStorePort
from pipeline.domain.ports.external_clip_downloader_port import ExternalClipDownloaderPort
from pipeline.domain.ports.file_delivery_port import FileDeliveryPort
from pipeline.domain.ports.file_storage_port import FileStoragePort
from pipeline.domain.ports.knowledge_base_port import KnowledgeBasePort
from pipeline.domain.ports.messaging_port import MessagingPort
from pipeline.domain.ports.model_dispatch_port import ModelDispatchPort
from pipeline.domain.ports.queue_port import QueuePort
from pipeline.domain.ports.resource_monitor_port import ResourceMonitorPort
from pipeline.domain.ports.sse_broadcast_port import SseBroadcastPort
from pipeline.domain.ports.state_store_port import StateStorePort
from pipeline.domain.ports.video_download_port import VideoDownloadPort
from pipeline.domain.ports.video_generation_port import VideoGenerationPort
from pipeline.domain.ports.video_processing_port import VideoProcessingPort

__all__ = [
    "AgentExecutionPort",
    "EventStorePort",
    "ExternalClipDownloaderPort",
    "FileDeliveryPort",
    "FileStoragePort",
=======
# New event-sourced port protocols (story 24-x series).
from pipeline.domain.ports.event_store_port import EventStorePort
from pipeline.domain.ports.state_store_port import StateStorePort as EventSourcedStateStorePort

# Backward-compatible re-exports: these maintain the original protocol signatures
# used by existing application and infrastructure adapters.
from pipeline.domain.ports_legacy import (
    AgentExecutionPort,
    ExternalClipDownloaderPort,
    FileDeliveryPort,
    KnowledgeBasePort,
    MessagingPort,
    ModelDispatchPort,
    QueuePort,
    ResourceMonitorPort,
    StateStorePort,
    VideoDownloadPort,
    VideoGenerationPort,
    VideoProcessingPort,
)

__all__ = [
    "AgentExecutionPort",
    "EventSourcedStateStorePort",
    "EventStorePort",
    "ExternalClipDownloaderPort",
    "FileDeliveryPort",
>>>>>>> worktree-agent-adf76045
    "KnowledgeBasePort",
    "MessagingPort",
    "ModelDispatchPort",
    "QueuePort",
    "ResourceMonitorPort",
<<<<<<< HEAD
    "SseBroadcastPort",
=======
>>>>>>> worktree-agent-adf76045
    "StateStorePort",
    "VideoDownloadPort",
    "VideoGenerationPort",
    "VideoProcessingPort",
]
<<<<<<< HEAD
=======
"""Domain ports — single-file Protocol interfaces for event-sourced state."""
>>>>>>> worktree-agent-a614ea7a
=======
>>>>>>> worktree-agent-adf76045
