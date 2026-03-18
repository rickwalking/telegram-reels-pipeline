"""Domain events — event-sourced state models for pipeline observability."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _freeze_mapping(mapping: Mapping[str, Any]) -> MappingProxyType[str, Any]:
    """Wrap a mutable mapping in MappingProxyType for deep immutability."""
    if isinstance(mapping, MappingProxyType):
        return mapping
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class PipelineStateEvent:
    """Immutable record of a single pipeline state transition.

    Each event captures what happened, when, and for which run.
    Events are append-only and form the authoritative state log.
    """

    event_type: str
    pipeline_run_id: str
    stage_name: str
    timestamp: str
    payload: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type must not be empty")
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.stage_name:
            raise ValueError("stage_name must not be empty")
        if not self.timestamp:
            raise ValueError("timestamp must not be empty")
        if not isinstance(self.payload, MappingProxyType):
            object.__setattr__(self, "payload", _freeze_mapping(self.payload))


@dataclass(frozen=True)
class RunStateProjection:
    """Read model projected from the event stream for a pipeline run.

    Updated by applying each PipelineStateEvent in order.
    Provides a snapshot of the current run state.
    """

    pipeline_run_id: str
    current_stage_name: str
    is_completed: bool
    is_failed: bool
    artifact_paths: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.pipeline_run_id:
            raise ValueError("pipeline_run_id must not be empty")
        if not self.current_stage_name:
            raise ValueError("current_stage_name must not be empty")
