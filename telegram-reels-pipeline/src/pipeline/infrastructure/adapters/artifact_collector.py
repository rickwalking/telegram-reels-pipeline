"""ArtifactCollector — scan workspace for agent output artifacts."""

from __future__ import annotations

from pathlib import Path

# File extensions considered valid artifacts
_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset({".md", ".json", ".txt", ".yaml", ".yml"})


def collect_artifacts(work_dir: Path) -> tuple[Path, ...]:
    """Scan work_dir for output files produced by the agent.

    Returns a sorted tuple of artifact paths matching expected extensions.
    Ignores hidden files (dotfiles). Only scans top-level files (not recursive).
    """
    if not work_dir.exists():
        return ()

    artifacts: list[Path] = []
    for path in sorted(work_dir.iterdir()):
        if path.is_file() and not path.name.startswith(".") and path.suffix in _ARTIFACT_EXTENSIONS:
            artifacts.append(path)
    return tuple(artifacts)
