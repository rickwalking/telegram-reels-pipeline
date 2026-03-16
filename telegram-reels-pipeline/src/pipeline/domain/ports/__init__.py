"""Domain ports package — re-exports all port protocols for backward compatibility."""

from __future__ import annotations

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
    "KnowledgeBasePort",
    "MessagingPort",
    "ModelDispatchPort",
    "QueuePort",
    "ResourceMonitorPort",
    "StateStorePort",
    "VideoDownloadPort",
    "VideoGenerationPort",
    "VideoProcessingPort",
]
