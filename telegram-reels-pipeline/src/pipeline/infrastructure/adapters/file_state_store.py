"""FileStateStore — async file-based RunState persistence with atomic writes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles

from pipeline.domain.models import RunState
from pipeline.domain.transitions import is_terminal
from pipeline.domain.types import RunId
from pipeline.infrastructure.adapters.frontmatter import deserialize_run_state, serialize_run_state

if TYPE_CHECKING:
    from pipeline.domain.ports import StateStorePort

logger = logging.getLogger(__name__)


class FileStateStore:
    """Persists RunState as YAML frontmatter in per-run run.md files.

    Satisfies the StateStorePort protocol.
    """

    if TYPE_CHECKING:
        _protocol_check: StateStorePort

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    async def save_state(self, state: RunState) -> None:
        """Serialize RunState and write atomically to {base_dir}/{run_id}/run.md."""
        run_dir = self._base_dir / str(state.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        target = run_dir / "run.md"
        tmp = target.with_suffix(".tmp")
        content = serialize_run_state(state)

        try:
            async with aiofiles.open(tmp, "w") as f:
                await f.write(content)
            tmp.rename(target)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

    async def load_state(self, run_id: RunId) -> RunState | None:
        """Read run.md and reconstruct RunState. Returns None if not found."""
        target = self._base_dir / str(run_id) / "run.md"
        try:
            async with aiofiles.open(target) as f:
                content = await f.read()
            return deserialize_run_state(content)
        except FileNotFoundError:
            return None

    async def list_incomplete_runs(self) -> list[RunState]:
        """Walk base_dir, load all run.md files, return non-terminal runs."""
        if not self._base_dir.exists():
            return []

        results: list[RunState] = []
        for run_dir in sorted(self._base_dir.iterdir()):
            run_file = run_dir / "run.md"
            if not run_file.is_file():
                continue
            try:
                async with aiofiles.open(run_file) as f:
                    content = await f.read()
                state = deserialize_run_state(content)
            except (ValueError, OSError) as exc:
                logger.warning("Skipping corrupted state file %s: %s", run_file, exc)
                continue
            if not is_terminal(state.current_stage):
                results.append(state)
        return results
