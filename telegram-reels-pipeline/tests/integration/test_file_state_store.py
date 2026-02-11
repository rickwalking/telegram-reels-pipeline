"""Integration tests for FileStateStore — real filesystem I/O."""

from pathlib import Path

import pytest

from pipeline.domain.enums import EscalationState, PipelineStage, QAStatus
from pipeline.domain.models import RunState
from pipeline.domain.types import RunId
from pipeline.infrastructure.adapters.file_state_store import FileStateStore
from pipeline.infrastructure.adapters.frontmatter import deserialize_run_state, serialize_run_state


@pytest.fixture
def store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(base_dir=tmp_path)


@pytest.fixture
def sample_state() -> RunState:
    return RunState(
        run_id=RunId("2026-02-10-abc123"),
        youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        current_stage=PipelineStage.RESEARCH,
        current_attempt=2,
        qa_status=QAStatus.REWORK,
        stages_completed=("router",),
        escalation_state=EscalationState.NONE,
        best_of_three_overrides=(),
        created_at="2026-02-10T14:00:00+00:00",
        updated_at="2026-02-10T14:05:00+00:00",
    )


class TestFrontmatterSerialization:
    def test_serialize_produces_frontmatter(self, sample_state: RunState) -> None:
        result = serialize_run_state(sample_state)
        assert result.startswith("---\n")
        assert result.endswith("---\n")
        assert "current_stage: research" in result
        assert "qa_status: rework" in result

    def test_deserialize_reconstructs_state(self, sample_state: RunState) -> None:
        content = serialize_run_state(sample_state)
        restored = deserialize_run_state(content)
        assert restored == sample_state

    def test_round_trip_all_enums(self) -> None:
        state = RunState(
            run_id=RunId("enum-test"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.LAYOUT_DETECTIVE,
            qa_status=QAStatus.FAILED,
            escalation_state=EscalationState.LAYOUT_UNKNOWN,
            stages_completed=("router", "research", "transcript", "content"),
            best_of_three_overrides=("transcript",),
            created_at="2026-02-10T14:00:00+00:00",
            updated_at="2026-02-10T14:30:00+00:00",
        )
        content = serialize_run_state(state)
        restored = deserialize_run_state(content)
        assert restored == state
        assert restored.current_stage == PipelineStage.LAYOUT_DETECTIVE
        assert restored.qa_status == QAStatus.FAILED
        assert restored.escalation_state == EscalationState.LAYOUT_UNKNOWN

    def test_deserialize_missing_delimiters_raises(self) -> None:
        with pytest.raises(ValueError, match="frontmatter delimiters"):
            deserialize_run_state("no delimiters here")

    def test_deserialize_empty_yaml_raises(self) -> None:
        with pytest.raises(ValueError, match="not a valid YAML mapping"):
            deserialize_run_state("---\n\n---\n")

    def test_deserialize_missing_required_key_raises(self) -> None:
        content = "---\nrun_id: test\nyoutube_url: https://example.com\n---\n"
        with pytest.raises(ValueError, match="Missing required key"):
            deserialize_run_state(content)

    def test_deserialize_content_not_starting_with_delimiters_raises(self) -> None:
        with pytest.raises(ValueError, match="frontmatter delimiters"):
            deserialize_run_state("some text\n---\nyaml: true\n---\n")


class TestFileStateStoreSave:
    async def test_save_creates_run_md(self, store: FileStateStore, sample_state: RunState, tmp_path: Path) -> None:
        await store.save_state(sample_state)
        run_file = tmp_path / "2026-02-10-abc123" / "run.md"
        assert run_file.exists()

    async def test_save_content_is_valid_frontmatter(
        self, store: FileStateStore, sample_state: RunState, tmp_path: Path
    ) -> None:
        await store.save_state(sample_state)
        content = (tmp_path / "2026-02-10-abc123" / "run.md").read_text()
        assert content.startswith("---\n")
        assert "run_id: 2026-02-10-abc123" in content

    async def test_save_atomic_no_tmp_left(self, store: FileStateStore, sample_state: RunState, tmp_path: Path) -> None:
        await store.save_state(sample_state)
        run_dir = tmp_path / "2026-02-10-abc123"
        tmp_files = list(run_dir.glob("*.tmp"))
        assert tmp_files == []

    async def test_save_overwrites_existing_state(self, store: FileStateStore, sample_state: RunState) -> None:
        from dataclasses import replace

        await store.save_state(sample_state)
        updated = replace(sample_state, current_stage=PipelineStage.TRANSCRIPT, current_attempt=1)
        await store.save_state(updated)
        loaded = await store.load_state(sample_state.run_id)
        assert loaded is not None
        assert loaded.current_stage == PipelineStage.TRANSCRIPT
        assert loaded != sample_state


class TestFileStateStoreLoad:
    async def test_load_returns_none_for_missing(self, store: FileStateStore) -> None:
        result = await store.load_state(RunId("nonexistent"))
        assert result is None

    async def test_load_round_trip(self, store: FileStateStore, sample_state: RunState) -> None:
        await store.save_state(sample_state)
        loaded = await store.load_state(RunId("2026-02-10-abc123"))
        assert loaded == sample_state

    async def test_load_preserves_all_fields(self, store: FileStateStore, sample_state: RunState) -> None:
        await store.save_state(sample_state)
        loaded = await store.load_state(RunId("2026-02-10-abc123"))
        assert loaded is not None
        assert loaded.run_id == RunId("2026-02-10-abc123")
        assert loaded.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert loaded.current_stage == PipelineStage.RESEARCH
        assert loaded.current_attempt == 2
        assert loaded.qa_status == QAStatus.REWORK
        assert loaded.stages_completed == ("router",)
        assert loaded.escalation_state == EscalationState.NONE
        assert loaded.created_at == "2026-02-10T14:00:00+00:00"
        assert loaded.updated_at == "2026-02-10T14:05:00+00:00"


class TestFileStateStoreListIncomplete:
    async def test_empty_dir_returns_empty(self, store: FileStateStore) -> None:
        result = await store.list_incomplete_runs()
        assert result == []

    async def test_finds_in_progress_runs(self, store: FileStateStore) -> None:
        state = RunState(
            run_id=RunId("in-progress-run"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.CONTENT,
        )
        await store.save_state(state)
        result = await store.list_incomplete_runs()
        assert len(result) == 1
        assert result[0].run_id == RunId("in-progress-run")

    async def test_excludes_completed_runs(self, store: FileStateStore) -> None:
        from dataclasses import replace

        active = RunState(
            run_id=RunId("active"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.RESEARCH,
        )
        completed = replace(
            RunState(
                run_id=RunId("done"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
            ),
            current_stage=PipelineStage.COMPLETED,
        )
        await store.save_state(active)
        await store.save_state(completed)
        result = await store.list_incomplete_runs()
        assert len(result) == 1
        assert result[0].run_id == RunId("active")

    async def test_excludes_failed_runs(self, store: FileStateStore) -> None:
        from dataclasses import replace

        failed = replace(
            RunState(
                run_id=RunId("failed"),
                youtube_url="https://youtube.com/watch?v=test",
                current_stage=PipelineStage.ROUTER,
            ),
            current_stage=PipelineStage.FAILED,
        )
        await store.save_state(failed)
        result = await store.list_incomplete_runs()
        assert result == []

    async def test_skips_corrupted_run_files(self, store: FileStateStore, tmp_path: Path) -> None:
        valid = RunState(
            run_id=RunId("valid-run"),
            youtube_url="https://youtube.com/watch?v=test",
            current_stage=PipelineStage.RESEARCH,
        )
        await store.save_state(valid)
        corrupt_dir = tmp_path / "corrupt-run"
        corrupt_dir.mkdir()
        (corrupt_dir / "run.md").write_text("---\ngarbage: true\n---\n")
        result = await store.list_incomplete_runs()
        assert len(result) == 1
        assert result[0].run_id == RunId("valid-run")
