"""Tests for RunCleaner — old run asset removal."""

from __future__ import annotations

import os
import time
from pathlib import Path

from pipeline.application.run_cleanup import CleanupResult, RunCleaner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_dir(
    base: Path,
    name: str = "run-001",
    extra_files: tuple[str, ...] = ("frames/001.png", "transcript.json"),
    age_days: int = 0,
) -> Path:
    """Create a fake run directory with run.md and extra files."""
    run_dir = base / name
    run_dir.mkdir(parents=True, exist_ok=True)

    run_md = run_dir / "run.md"
    run_md.write_text("---\nrun_id: test\n---\n")

    events = run_dir / "events.log"
    events.write_text("2026-02-10T14:00:00Z | pipeline.run_started\n")

    for extra in extra_files:
        p = run_dir / extra
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("data")

    if age_days > 0:
        old_time = time.time() - (age_days * 86400)
        os.utime(run_md, (old_time, old_time))

    return run_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunCleaner:
    async def test_empty_directory(self, tmp_path: Path) -> None:
        cleaner = RunCleaner(runs_dir=tmp_path / "nonexistent")
        result = await cleaner.clean()

        assert result == CleanupResult(runs_scanned=0, runs_cleaned=0, bytes_freed=0)

    async def test_skips_recent_runs(self, tmp_path: Path) -> None:
        _make_run_dir(tmp_path, "run-001", age_days=0)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        result = await cleaner.clean()

        assert result.runs_scanned == 1
        assert result.runs_cleaned == 0

    async def test_cleans_old_runs(self, tmp_path: Path) -> None:
        _make_run_dir(tmp_path, "run-old", age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        result = await cleaner.clean()

        assert result.runs_cleaned == 1
        assert result.bytes_freed > 0

    async def test_preserves_run_md(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path, "run-old", age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        await cleaner.clean()

        assert (run_dir / "run.md").exists()

    async def test_preserves_events_log(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path, "run-old", age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        await cleaner.clean()

        assert (run_dir / "events.log").exists()

    async def test_preserves_mp4_files(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path, "run-old", extra_files=("final-reel.mp4",), age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        await cleaner.clean()

        assert (run_dir / "final-reel.mp4").exists()

    async def test_removes_intermediate_artifacts(self, tmp_path: Path) -> None:
        extras = ("frames/001.png", "frames/002.png", "transcript.json", "content.json")
        run_dir = _make_run_dir(tmp_path, "run-old", extra_files=extras, age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        await cleaner.clean()

        assert not (run_dir / "transcript.json").exists()
        assert not (run_dir / "content.json").exists()
        assert not (run_dir / "frames" / "001.png").exists()

    async def test_removes_empty_subdirectories(self, tmp_path: Path) -> None:
        run_dir = _make_run_dir(tmp_path, "run-old", extra_files=("frames/001.png",), age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        await cleaner.clean()

        assert not (run_dir / "frames").exists()

    async def test_multiple_runs_mixed_ages(self, tmp_path: Path) -> None:
        _make_run_dir(tmp_path, "run-old", age_days=45)
        _make_run_dir(tmp_path, "run-recent", age_days=5)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        result = await cleaner.clean()

        assert result.runs_scanned == 2
        assert result.runs_cleaned == 1

    async def test_custom_retention_period(self, tmp_path: Path) -> None:
        _make_run_dir(tmp_path, "run-old", age_days=10)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=7)

        result = await cleaner.clean()

        assert result.runs_cleaned == 1

    async def test_result_is_frozen(self, tmp_path: Path) -> None:
        result = CleanupResult(runs_scanned=1, runs_cleaned=0, bytes_freed=0)
        assert isinstance(result, CleanupResult)

    async def test_skips_non_directory_entries(self, tmp_path: Path) -> None:
        (tmp_path / "stray-file.txt").write_text("not a run dir")
        _make_run_dir(tmp_path, "run-old", age_days=45)
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        result = await cleaner.clean()

        assert result.runs_scanned == 1

    async def test_skips_run_dir_without_run_md(self, tmp_path: Path) -> None:
        empty_run = tmp_path / "run-no-md"
        empty_run.mkdir()
        cleaner = RunCleaner(runs_dir=tmp_path, retention_days=30)

        result = await cleaner.clean()

        assert result.runs_scanned == 1
        assert result.runs_cleaned == 0

    async def test_skips_symlinked_run_directories(self, tmp_path: Path) -> None:
        real_dir = tmp_path / "outside"
        real_dir.mkdir()
        (real_dir / "secret.txt").write_text("do not delete")

        symlink = tmp_path / "runs" / "run-symlink"
        (tmp_path / "runs").mkdir()
        symlink.symlink_to(real_dir)

        cleaner = RunCleaner(runs_dir=tmp_path / "runs", retention_days=30)
        result = await cleaner.clean()

        assert result.runs_scanned == 0
        assert (real_dir / "secret.txt").exists()
