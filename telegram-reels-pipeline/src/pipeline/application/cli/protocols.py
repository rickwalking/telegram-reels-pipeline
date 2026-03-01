"""CLI protocols — Command pattern interfaces for pipeline CLI operations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from pipeline.domain.enums import PipelineStage

if TYPE_CHECKING:
    from pipeline.application.cli.context import PipelineContext


@dataclass(frozen=True)
class CommandResult:
    """Immutable result returned by a Command execution."""

    success: bool
    message: str
    data: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if not isinstance(self.data, MappingProxyType):
            object.__setattr__(self, "data", MappingProxyType(dict(self.data)))


@runtime_checkable
class Command(Protocol):
    """Command protocol — encapsulates a single pipeline CLI operation."""

    @property
    def name(self) -> str: ...

    async def execute(self, context: PipelineContext) -> CommandResult: ...


@runtime_checkable
class StageHook(Protocol):
    """Hook that runs before or after a pipeline stage."""

    def should_run(self, stage: PipelineStage, phase: Literal["pre", "post"]) -> bool: ...

    async def execute(self, context: PipelineContext) -> None: ...


@runtime_checkable
class InputReader(Protocol):
    """Abstraction over stdin for testability."""

    async def read(self, prompt: str, timeout: int) -> str | None: ...


@runtime_checkable
class ClipDurationProber(Protocol):
    """Abstraction over ffprobe for clip duration queries."""

    async def probe(self, clip_path: Path) -> float | None: ...


@runtime_checkable
class ArtifactCollector(Protocol):
    """Scan a workspace directory for output artifacts."""

    def __call__(self, work_dir: Path) -> tuple[Path, ...]: ...


@runtime_checkable
class OutputPort(Protocol):
    """Write user-facing text (matches builtin ``print`` signature)."""

    def __call__(self, *args: object, **kwargs: Any) -> None: ...
