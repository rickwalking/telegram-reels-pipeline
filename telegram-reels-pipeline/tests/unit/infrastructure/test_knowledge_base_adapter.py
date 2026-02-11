"""Tests for YamlKnowledgeBase — CRUD on crop-strategies.yaml."""

from __future__ import annotations

from pathlib import Path

from pipeline.domain.models import CropRegion
from pipeline.infrastructure.adapters.knowledge_base_adapter import YamlKnowledgeBase


class TestYamlKnowledgeBaseGetStrategy:
    async def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        kb = YamlKnowledgeBase(path=tmp_path / "missing.yaml")
        result = await kb.get_strategy("side_by_side")
        assert result is None

    async def test_returns_none_for_unknown_layout(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("side_by_side:\n  x: 0\n  y: 0\n  width: 540\n  height: 1080\n")
        kb = YamlKnowledgeBase(path=path)
        result = await kb.get_strategy("nonexistent")
        assert result is None

    async def test_returns_crop_region(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("side_by_side:\n  x: 100\n  y: 50\n  width: 540\n  height: 960\n")
        kb = YamlKnowledgeBase(path=path)
        result = await kb.get_strategy("side_by_side")
        assert result is not None
        assert result == CropRegion(x=100, y=50, width=540, height=960, layout_name="side_by_side")

    async def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("")
        kb = YamlKnowledgeBase(path=path)
        assert await kb.get_strategy("any") is None


class TestYamlKnowledgeBaseSaveStrategy:
    async def test_saves_new_strategy(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        kb = YamlKnowledgeBase(path=path)
        region = CropRegion(x=0, y=0, width=540, height=1080, layout_name="custom_layout")
        await kb.save_strategy("custom_layout", region)

        # Verify it was saved
        result = await kb.get_strategy("custom_layout")
        assert result is not None
        assert result.x == 0
        assert result.width == 540

    async def test_updates_existing_strategy(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("side_by_side:\n  x: 0\n  y: 0\n  width: 540\n  height: 1080\n")
        kb = YamlKnowledgeBase(path=path)

        new_region = CropRegion(x=100, y=0, width=600, height=1080)
        await kb.save_strategy("side_by_side", new_region)

        result = await kb.get_strategy("side_by_side")
        assert result is not None
        assert result.x == 100
        assert result.width == 600

    async def test_preserves_other_strategies(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("existing:\n  x: 1\n  y: 2\n  width: 3\n  height: 4\n")
        kb = YamlKnowledgeBase(path=path)

        await kb.save_strategy("new_one", CropRegion(x=10, y=20, width=30, height=40))

        existing = await kb.get_strategy("existing")
        assert existing is not None
        assert existing.x == 1

    async def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "strategies.yaml"
        kb = YamlKnowledgeBase(path=path)
        await kb.save_strategy("test", CropRegion(x=0, y=0, width=100, height=200))
        assert path.exists()

    async def test_atomic_write_no_tmp_file_remains(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        kb = YamlKnowledgeBase(path=path)
        await kb.save_strategy("test", CropRegion(x=0, y=0, width=100, height=200))
        # No .tmp file should remain
        assert not path.with_suffix(".tmp").exists()


class TestYamlKnowledgeBaseListStrategies:
    async def test_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        path.write_text("")
        kb = YamlKnowledgeBase(path=path)
        result = await kb.list_strategies()
        assert result == {}

    async def test_lists_all_strategies(self, tmp_path: Path) -> None:
        path = tmp_path / "strategies.yaml"
        kb = YamlKnowledgeBase(path=path)
        await kb.save_strategy("a", CropRegion(x=1, y=2, width=3, height=4))
        await kb.save_strategy("b", CropRegion(x=5, y=6, width=7, height=8))

        result = await kb.list_strategies()
        assert len(result) == 2
        assert "a" in result
        assert "b" in result
        assert result["a"].x == 1
        assert result["b"].width == 7

    async def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        kb = YamlKnowledgeBase(path=tmp_path / "missing.yaml")
        result = await kb.list_strategies()
        assert result == {}


class TestYamlKnowledgeBaseProtocol:
    def test_satisfies_knowledge_base_port(self, tmp_path: Path) -> None:
        from pipeline.domain.ports import KnowledgeBasePort

        kb = YamlKnowledgeBase(path=tmp_path / "test.yaml")
        assert isinstance(kb, KnowledgeBasePort)
