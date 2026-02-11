"""Tests for ArtifactCollector — workspace artifact scanning."""

from pathlib import Path

from pipeline.infrastructure.adapters.artifact_collector import collect_artifacts


class TestCollectArtifacts:
    def test_collects_md_files(self, tmp_path: Path) -> None:
        (tmp_path / "output.md").write_text("result")
        result = collect_artifacts(tmp_path)
        assert len(result) == 1
        assert result[0].name == "output.md"

    def test_collects_json_files(self, tmp_path: Path) -> None:
        (tmp_path / "data.json").write_text("{}")
        result = collect_artifacts(tmp_path)
        assert len(result) == 1
        assert result[0].name == "data.json"

    def test_collects_multiple_types(self, tmp_path: Path) -> None:
        (tmp_path / "doc.md").write_text("text")
        (tmp_path / "config.yaml").write_text("key: val")
        (tmp_path / "notes.txt").write_text("notes")
        result = collect_artifacts(tmp_path)
        assert len(result) == 3

    def test_returns_empty_for_empty_dir(self, tmp_path: Path) -> None:
        result = collect_artifacts(tmp_path)
        assert result == ()

    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path) -> None:
        missing = tmp_path / "no-such-dir"
        result = collect_artifacts(missing)
        assert result == ()

    def test_ignores_hidden_files(self, tmp_path: Path) -> None:
        (tmp_path / ".hidden.md").write_text("secret")
        (tmp_path / "visible.md").write_text("public")
        result = collect_artifacts(tmp_path)
        assert len(result) == 1
        assert result[0].name == "visible.md"

    def test_ignores_non_artifact_extensions(self, tmp_path: Path) -> None:
        (tmp_path / "image.png").write_text("binary")
        (tmp_path / "archive.zip").write_text("binary")
        (tmp_path / "good.md").write_text("text")
        result = collect_artifacts(tmp_path)
        assert len(result) == 1

    def test_collects_mp4_files(self, tmp_path: Path) -> None:
        (tmp_path / "segment-001.mp4").write_text("video")
        (tmp_path / "final-reel.mp4").write_text("video")
        result = collect_artifacts(tmp_path)
        assert len(result) == 2
        assert all(p.suffix == ".mp4" for p in result)

    def test_returns_sorted_paths(self, tmp_path: Path) -> None:
        (tmp_path / "z_last.md").write_text("")
        (tmp_path / "a_first.md").write_text("")
        (tmp_path / "m_middle.md").write_text("")
        result = collect_artifacts(tmp_path)
        names = [p.name for p in result]
        assert names == ["a_first.md", "m_middle.md", "z_last.md"]

    def test_returns_tuple(self, tmp_path: Path) -> None:
        (tmp_path / "file.md").write_text("")
        result = collect_artifacts(tmp_path)
        assert isinstance(result, tuple)

    def test_ignores_directories(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.md").write_text("")
        result = collect_artifacts(tmp_path)
        assert len(result) == 1
